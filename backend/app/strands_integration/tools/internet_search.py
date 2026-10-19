import html
import logging
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor

import requests
from app.bedrock import call_converse_api, get_model_id, get_text_from_converse_response
from app.repositories.models.custom_bot import BotModel
from app.usecases.global_config import get_title_model
from strands import tool
from strands.types.tools import AgentTool as StrandsAgentTool

logger = logging.getLogger(__name__)


def _split_locale(locale: str) -> tuple[str, str]:
    """Split `{language}-{country}`; the country is empty when the model gives none."""
    language, _, country = (locale or "en-us").lower().partition("-")
    return language, country


def _search_with_duckduckgo_standalone(
    query: str, time_limit: str, locale: str
) -> list[dict[str, str]]:
    """Search with DuckDuckGo, using the result snippets as the content."""
    from duckduckgo_search import DDGS

    language, country = _split_locale(locale)
    # DuckDuckGo regions are `{country}-{language}`; `wt-wt` is no region.
    region = f"{country}-{language}" if country else "wt-wt"
    logger.info(
        "Executing DuckDuckGo search: query_chars=%d, region=%s, time_limit=%s",
        len(query),
        region,
        time_limit,
    )
    with DDGS() as ddgs:
        results = ddgs.text(
            keywords=query,
            region=region,
            safesearch="moderate",
            timelimit=time_limit or None,
            max_results=20,
            backend="api",
        )
    logger.info("DuckDuckGo search completed. Found %d results", len(results))
    return [
        {
            "content": result["body"],
            "source_name": result["title"],
            "source_link": result["href"],
        }
        for result in results
    ]


def _search_with_firecrawl_standalone(
    query: str, api_key: str, locale: str, max_results: int = 10
) -> list[dict[str, str]]:
    """Search with Firecrawl, which returns whole pages, and summarize each page."""
    from firecrawl import FirecrawlApp, ScrapeOptions

    logger.info(
        "Searching with Firecrawl: query_chars=%d, max_results=%d, locale=%s",
        len(query),
        max_results,
        locale,
    )
    language, country = _split_locale(locale)
    response = FirecrawlApp(api_key=api_key).search(
        query,
        limit=max_results,
        lang=language,
        location=country or None,
        scrape_options=ScrapeOptions(formats=["markdown"], onlyMainContent=True),
    )
    pages = [
        (
            page.get("title", ""),
            page.get("url", "") or page.get("metadata", {}).get("sourceURL", ""),
            page.get("markdown", "") or page.get("content", ""),
        )
        for page in response.data
    ]
    pages = [(title, url, content) for title, url, content in pages if title or content]
    # The summaries are independent model calls, so they run at once.
    with ThreadPoolExecutor(max_workers=_MAX_PARALLEL_SUMMARIES) as executor:
        summaries = list(
            executor.map(
                lambda page: _summarize_content_standalone(
                    page[2], page[0], page[1], query
                ),
                pages,
            )
        )
    logger.info("Firecrawl search completed. Found %d results", len(pages))
    return [
        {"content": summary, "source_name": title, "source_link": url}
        for (title, url, _), summary in zip(pages, summaries)
    ]


# (connect, read) seconds for the search APIs.
_SEARCH_API_TIMEOUT = (5, 20)
_MAX_ATTEMPTS = 3
_MAX_PARALLEL_SUMMARIES = 8
_MAX_RETRY_DELAY = 5.0
_RETRYABLE_STATUSES = {429, 500, 502, 503, 504}
_TAVILY_TIME_RANGES = {"d": "day", "w": "week", "m": "month", "y": "year"}
_BRAVE_FRESHNESS = {"d": "pd", "w": "pw", "m": "pm", "y": "py"}


def _retry_delay(response: requests.Response, attempt: int) -> float:
    """Seconds to wait before the next attempt: `Retry-After` if the API sends it."""
    retry_after = response.headers.get("Retry-After", "")
    if retry_after.isdigit():
        return float(retry_after)
    return min(2**attempt, _MAX_RETRY_DELAY) * random.uniform(0.5, 1)


def _call_search_api(engine: str, method: str, url: str, **kwargs) -> dict:
    """Call a search API, retrying rate limits and server errors a few times.

    A search is a read, so a retry is safe. Timeouts are not retried: the request
    timeout already bounds the wait, and a retry would double it. The model often searches several queries
    at once, which exceeds per-second plans such as Brave's free one. The errors name
    only the engine and the status, because the request URL can hold the query.
    """
    for attempt in range(_MAX_ATTEMPTS):
        try:
            response = requests.request(
                method, url, timeout=_SEARCH_API_TIMEOUT, **kwargs
            )
        except requests.RequestException as e:
            raise RuntimeError(f"{engine} search failed: {type(e).__name__}") from None
        if response.ok:
            return response.json()
        if (
            response.status_code not in _RETRYABLE_STATUSES
            or attempt == _MAX_ATTEMPTS - 1
        ):
            break
        delay = _retry_delay(response, attempt)
        if delay > _MAX_RETRY_DELAY:
            # The limit lasts longer than a chat turn should wait.
            break
        logger.warning(
            "%s search returned HTTP %d, retrying in %.1f s",
            engine,
            response.status_code,
            delay,
        )
        time.sleep(delay)
    raise RuntimeError(f"{engine} search returned HTTP {response.status_code}")


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
    # The locale is `{language}-{country}`; Brave takes the country code only.
    _, _, country = locale.partition("-")
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


def _search(
    bot: BotModel | None, query: str, locale: str, time_limit: str
) -> list[dict[str, str]]:
    """Search with the engine of the bot; DuckDuckGo without a bot or a setting."""
    internet_tool = _get_internet_tool_config(bot)
    engine = internet_tool.search_engine if internet_tool else "duckduckgo"
    if engine == "duckduckgo":
        return _search_with_duckduckgo_standalone(query, time_limit, locale)

    config = internet_tool.search_api_config if internet_tool else None
    if config is None:
        # The bot schema requires the key, so only a broken item gets here.
        raise RuntimeError(f"The bot has no API key for {engine}")
    if engine == "tavily":
        return _search_with_tavily(
            query, config.api_key, time_limit, config.max_results
        )
    if engine == "brave":
        return _search_with_brave(
            query, config.api_key, time_limit, locale, config.max_results
        )
    return _search_with_firecrawl_standalone(
        query, config.api_key, locale, config.max_results
    )


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
            time_limit: Retrieve only the most recent results, for example `w` only returns the results from the last week. Units are 'd' (day), 'w' (week), 'm' (month), 'y' (year). Use empty string to retrieve all results.

        Returns:
            dict: ToolResult format with search results in json field
        """
        try:
            results = _search(bot, query, locale, time_limit)
            # Return in ToolResult format to prevent Strands from converting to string
            return {
                "status": "success",
                "content": [{"json": result} for result in results],
            }

        except Exception:
            # Error texts can name internal resources; the model and the
            # conversation get a fixed text.
            logger.exception("Internet search failed")
            return {
                "status": "error",
                "content": [{"text": "The internet search failed."}],
            }

    return internet_search
