import html
import logging
import re

import requests
from app.bedrock import call_converse_api, get_model_id, get_text_from_converse_response
from app.repositories.models.custom_bot import BotModel
from app.usecases.global_config import get_title_model
from strands import tool
from strands.types.tools import AgentTool as StrandsAgentTool

logger = logging.getLogger(__name__)


def _search_with_duckduckgo_standalone(
    query: str, time_limit: str, locale: str
) -> list[dict[str, str]]:
    """Standalone DuckDuckGo search implementation."""
    try:
        from duckduckgo_search import DDGS

        language, country = locale.split("-", 1)
        REGION = f"{country}-{language}".lower()
        SAFE_SEARCH = "moderate"
        MAX_RESULTS = 20
        BACKEND = "api"

        logger.info(
            f"Executing DuckDuckGo search: query_chars={len(query)}, region={REGION}, time_limit={time_limit}"
        )

        with DDGS() as ddgs:
            results = list(
                ddgs.text(
                    keywords=query,
                    region=REGION,
                    safesearch=SAFE_SEARCH,
                    timelimit=time_limit,
                    max_results=MAX_RESULTS,
                    backend=BACKEND,
                )
            )

        # Format results for citation support
        formatted_results = []
        for result in results:
            formatted_results.append(
                {
                    "content": _summarize_content_standalone(
                        result["body"], result["title"], result["href"], query
                    ),
                    "source_name": result["title"],
                    "source_link": result["href"],
                }
            )

        logger.info(
            f"DuckDuckGo search completed. Found {len(formatted_results)} results"
        )
        return formatted_results

    except Exception as e:
        logger.error(f"DuckDuckGo search error: {e}")
        raise e


def _search_with_firecrawl_standalone(
    query: str, api_key: str, locale: str, max_results: int = 10
) -> list[dict[str, str]]:
    """Standalone Firecrawl search implementation."""
    try:
        from firecrawl import FirecrawlApp, ScrapeOptions

        logger.info(
            f"Searching with Firecrawl: query_chars={len(query)}, max_results={max_results} locale={locale}"
        )

        app = FirecrawlApp(api_key=api_key)

        # Incoming locale is language-country (e.g. 'en-us').
        language, country = locale.split("-", 1)
        results = app.search(
            query,
            limit=max_results,
            lang=language,
            location=country,
            scrape_options=ScrapeOptions(formats=["markdown"], onlyMainContent=True),
        )

        if not results or not hasattr(results, "data") or not results.data:
            logger.warning("No results found from Firecrawl")
            return []

        # Format results
        formatted_results = []
        for data in results.data:
            if isinstance(data, dict):
                title = data.get("title", "")
                url = data.get("url", "") or (
                    data.get("metadata", {}).get("sourceURL", "")
                    if isinstance(data.get("metadata"), dict)
                    else ""
                )
                content = data.get("markdown", "") or data.get("content", "")

                if title or content:
                    formatted_results.append(
                        {
                            "content": _summarize_content_standalone(
                                content, title, url, query
                            ),
                            "source_name": title,
                            "source_link": url,
                        }
                    )

        logger.info(
            f"Firecrawl search completed. Found {len(formatted_results)} results"
        )
        return formatted_results

    except Exception as e:
        logger.error(f"Firecrawl search error: {e}")
        # Instead of raising, return empty list to allow fallback
        return []


# (connect, read) seconds for the search APIs.
_SEARCH_API_TIMEOUT = (5, 20)
_TAVILY_TIME_RANGES = {"d": "day", "w": "week", "m": "month", "y": "year"}
_BRAVE_FRESHNESS = {"d": "pd", "w": "pw", "m": "pm", "y": "py"}


def _call_search_api(engine: str, method: str, url: str, **kwargs) -> dict:
    """Call a search API. The errors name only the engine and the status, because
    the request URL can hold the query."""
    try:
        response = requests.request(method, url, timeout=_SEARCH_API_TIMEOUT, **kwargs)
    except requests.RequestException as e:
        raise RuntimeError(f"{engine} search failed: {type(e).__name__}") from None
    if not response.ok:
        raise RuntimeError(f"{engine} search returned HTTP {response.status_code}")
    return response.json()


def _search_with_tavily(
    query: str, api_key: str, time_limit: str, max_results: int
) -> list[dict[str, str]]:
    """Search with Tavily, whose results already carry the content relevant to the query."""
    body: dict = {"query": query, "max_results": max_results}
    if time_limit in _TAVILY_TIME_RANGES:
        body["time_range"] = _TAVILY_TIME_RANGES[time_limit]
    results = _call_search_api(
        "Tavily",
        "POST",
        "https://api.tavily.com/search",
        headers={"Authorization": f"Bearer {api_key}"},
        json=body,
    ).get("results", [])
    logger.info("Tavily search completed. Found %d results", len(results))
    return [
        {
            "content": result.get("content", ""),
            "source_name": result.get("title", ""),
            "source_link": result.get("url", ""),
        }
        for result in results
    ]


def _plain_text(snippet: str) -> str:
    """Brave marks the matched words in its snippets with HTML tags."""
    return html.unescape(re.sub(r"<[^>]+>", "", snippet))


def _search_with_brave(
    query: str, api_key: str, time_limit: str, locale: str, max_results: int
) -> list[dict[str, str]]:
    """Search with the Brave Search API, using the result snippets as the content."""
    params: dict = {"q": query, "count": max_results}
    country = locale.split("-", 1)[-1]
    if len(country) == 2:
        params["country"] = country.upper()
    if time_limit in _BRAVE_FRESHNESS:
        params["freshness"] = _BRAVE_FRESHNESS[time_limit]
    results = (
        _call_search_api(
            "Brave",
            "GET",
            "https://api.search.brave.com/res/v1/web/search",
            headers={"Accept": "application/json", "X-Subscription-Token": api_key},
            params=params,
        )
        .get("web", {})
        .get("results", [])
    )
    logger.info("Brave search completed. Found %d results", len(results))
    return [
        {
            "content": "\n".join(
                _plain_text(snippet)
                for snippet in [result.get("description", "")]
                + result.get("extra_snippets", [])
                if snippet
            ),
            "source_name": result.get("title", ""),
            "source_link": result.get("url", ""),
        }
        for result in results
    ]


def _summarize_content_standalone(
    content: str, title: str, url: str, query: str
) -> str:
    """Standalone content summarization."""
    try:
        # Truncate content if too long
        max_input_length = 8000
        if len(content) > max_input_length:
            content = content[:max_input_length] + "..."

        prompt = f"""Please provide a concise summary of the following web content in 500-800 tokens maximum. Focus on information that directly answers or relates to the user's query: "{query}"

Title: {title}
URL: {url}
Content: {content}

Summary:"""

        # Summaries are short, so they use the same lightweight model as titles.
        response = call_converse_api(
            {
                "modelId": get_model_id(get_title_model()),
                "messages": [{"role": "user", "content": [{"text": prompt}]}],
                "inferenceConfig": {"maxTokens": 800},
            }
        )
        summary = get_text_from_converse_response(response).strip()

        logger.info(
            f"Summarized content from {len(content)} chars to {len(summary)} chars"
        )
        return summary

    except Exception as e:
        logger.error(f"Error summarizing content: {e}")
        # Fallback: return truncated content
        fallback_content = content[:1000] + "..." if len(content) > 1000 else content
        return fallback_content


def _get_internet_tool_config(bot: BotModel | None):
    """Extract internet tool configuration from bot."""
    if not bot or not bot.agent or not bot.agent.tools:
        return None

    for tool_config in bot.agent.tools:
        if tool_config.tool_type == "internet":
            return tool_config

    return None


def create_internet_search_tool(bot: BotModel | None) -> StrandsAgentTool:
    """Create an internet search tool with bot context captured in closure."""

    @tool
    def internet_search(
        query: str, locale: str = "en-us", time_limit: str = "d"
    ) -> dict:
        """
        Search the internet for information.

        Args:
            query: The query to search for on the internet.
            locale: The country code and language code for the search. Must be `{language}-{country}` for example `jp-jp` (Japanese - Japan), `zh-cn` (Chinese - China), `en-ca` (English - Canada), `fr-ca` (French - Canada), `en-nz` (English - New Zealand), etc. If empty the default is `en-us`.
            time_limit: Retrieve only the most recent results, for example `1w` only returns the results from the last week. Units are 'd' (day), 'w' (week), 'm' (month), 'y' (year). Use empty string to retrieve all results.

        Returns:
            dict: ToolResult format with search results in json field
        """
        logger.debug(
            f"[INTERNET_SEARCH_V3] Starting search: query={query}, locale={locale}, time_limit={time_limit}"
        )

        try:
            # # Bot is captured on closure
            current_bot = bot

            # Use DuckDuckGo if no bot context
            if not current_bot:
                logger.debug("[INTERNET_SEARCH_V3] No bot context, using DuckDuckGo")
                results = _search_with_duckduckgo_standalone(query, time_limit, locale)
            else:
                internet_tool = _get_internet_tool_config(current_bot)
                engine = internet_tool.search_engine if internet_tool else None
                config = internet_tool.search_api_config if internet_tool else None

                if engine == "tavily" and config:
                    results = _search_with_tavily(
                        query, config.api_key, time_limit, config.max_results
                    )
                elif engine == "brave" and config:
                    results = _search_with_brave(
                        query, config.api_key, time_limit, locale, config.max_results
                    )
                elif engine == "firecrawl" and config and config.api_key:
                    logger.debug("[INTERNET_SEARCH_V3] Using Firecrawl search")
                    results = _search_with_firecrawl_standalone(
                        query=query,
                        api_key=config.api_key,
                        locale=locale,
                        max_results=config.max_results,
                    )

                    # If no results from Firecrawl, fallback to DuckDuckGo
                    if not results:
                        logger.warning(
                            "[INTERNET_SEARCH_V3] Firecrawl returned no results, falling back to DuckDuckGo"
                        )
                        results = _search_with_duckduckgo_standalone(
                            query, time_limit, locale
                        )
                else:
                    logger.debug("[INTERNET_SEARCH_V3] Using DuckDuckGo search")
                    results = _search_with_duckduckgo_standalone(
                        query, time_limit, locale
                    )

            # Return in ToolResult format to prevent Strands from converting to string
            return {
                "status": "success",
                "content": [{"json": result} for result in results],
            }

        except Exception:
            # Error texts can name internal resources; the model and the
            # conversation get a fixed text.
            logger.exception("[INTERNET_SEARCH_V3] Internet search failed")
            return {
                "status": "error",
                "content": [{"text": "The internet search failed."}],
            }

    return internet_search
