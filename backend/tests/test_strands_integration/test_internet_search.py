"""The search API requests and the results that the model gets."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
import requests
from app.repositories.models.custom_bot import InternetToolModel
from app.strands_integration.tools import internet_search

API_KEY = "test-api-key"


def bot_with(engine: str, keyed: bool = True) -> MagicMock:
    tool = InternetToolModel.model_construct(
        tool_type="internet",
        name="internet_search",
        description="",
        search_engine=engine,
        search_api_config=(
            MagicMock(api_key=API_KEY, max_results=3) if keyed else None
        ),
    )
    return MagicMock(internet_tool=MagicMock(return_value=tool))


def search(engine: str, payload: dict, **kwargs) -> tuple[dict, MagicMock]:
    response = MagicMock(ok=True, status_code=200)
    response.json.return_value = payload
    tool = internet_search.create_internet_search_tool(bot_with(engine))
    with patch.object(
        internet_search.requests, "request", return_value=response
    ) as request:
        return tool(query="weather", **kwargs), request


def test_tavily():
    result, request = search(
        "tavily",
        {"results": [{"title": "T", "url": "https://t", "content": "sunny"}]},
        time_limit="w",
    )

    method, url = request.call_args.args
    assert (method, url) == ("POST", "https://api.tavily.com/search")
    assert request.call_args.kwargs["headers"] == {"Authorization": f"Bearer {API_KEY}"}
    assert request.call_args.kwargs["json"] == {
        "query": "weather",
        "max_results": 3,
        "time_range": "week",
    }
    assert result["status"] == "success"
    assert result["content"] == [
        {"json": {"content": "sunny", "source_name": "T", "source_link": "https://t"}}
    ]


def test_brave():
    result, request = search(
        "brave",
        {
            "web": {
                "results": [
                    {
                        "title": "B",
                        "url": "https://b",
                        "description": "<strong>Rain</strong> &amp; wind",
                        "extra_snippets": ["Cold"],
                    }
                ]
            }
        },
        locale="ko-kr",
        time_limit="",
    )

    assert request.call_args.args[0] == "GET"
    assert request.call_args.kwargs["headers"]["X-Subscription-Token"] == API_KEY
    # No freshness for all results.
    assert request.call_args.kwargs["params"] == {
        "q": "weather",
        "count": 3,
        "country": "KR",
    }
    assert result["content"] == [
        {
            "json": {
                "content": "Rain & wind\nCold",
                "source_name": "B",
                "source_link": "https://b",
            }
        }
    ]


@pytest.mark.parametrize("locale", ["en", "en-", "zh-hans"])
def test_brave_sends_no_country_that_the_locale_does_not_give(locale):
    _, request = search("brave", {}, locale=locale)

    assert "country" not in request.call_args.kwargs["params"]


def failing(status: int, headers: dict | None = None) -> MagicMock:
    return MagicMock(ok=False, status_code=status, headers=headers or {})


@pytest.mark.parametrize("engine", ["tavily", "brave"])
def test_a_failed_request_is_a_tool_error_without_the_query(engine, caplog):
    tool = internet_search.create_internet_search_tool(bot_with(engine))
    with patch.object(
        internet_search.requests, "request", return_value=failing(401)
    ), patch.object(internet_search.time, "sleep") as sleep:
        result = tool(query="private words")
    with patch.object(
        internet_search.requests,
        "request",
        side_effect=requests.ConnectionError("https://x/?q=private words"),
    ):
        failed_connection = tool(query="private words")

    for failure in (result, failed_connection):
        assert failure["status"] == "error"
    # An invalid key is not retried.
    sleep.assert_not_called()
    assert "HTTP 401" in caplog.text
    # The model learns why, so it can tell the user.
    assert result["content"] == [
        {
            "text": f"The internet search failed: {engine.capitalize()} search returned HTTP 401."
        }
    ]
    # The request URL holds the query.
    assert "private words" not in caplog.text


def test_rate_limits_are_retried_as_the_api_asks():
    ok = MagicMock(ok=True, status_code=200)
    ok.json.return_value = {"results": []}
    with patch.object(
        internet_search.requests,
        "request",
        side_effect=[failing(429, {"Retry-After": "2"}), failing(503), ok],
    ) as request, patch.object(internet_search.time, "sleep") as sleep:
        internet_search._call_search_api("Tavily", "POST", "https://t")

    assert request.call_count == 3
    first, second = (c.args[0] for c in sleep.call_args_list)
    assert first == 2
    # Without Retry-After, the wait grows and has jitter.
    assert 1 <= second <= 2


def test_a_lasting_rate_limit_fails_after_the_last_attempt():
    with patch.object(
        internet_search.requests, "request", return_value=failing(429)
    ) as request, patch.object(internet_search.time, "sleep"):
        with pytest.raises(RuntimeError, match="HTTP 429"):
            internet_search._call_search_api("Brave", "GET", "https://b")

    assert request.call_count == internet_search._MAX_ATTEMPTS


def test_a_long_retry_after_fails_without_waiting():
    with patch.object(
        internet_search.requests,
        "request",
        return_value=failing(429, {"Retry-After": "60"}),
    ) as request, patch.object(internet_search.time, "sleep") as sleep:
        with pytest.raises(RuntimeError, match="HTTP 429"):
            internet_search._call_search_api("Brave", "GET", "https://b")

    assert request.call_count == 1
    sleep.assert_not_called()


@pytest.mark.parametrize(
    "locale, expected",
    [
        ("ko-kr", ("ko", "kr")),
        ("EN-US", ("en", "us")),
        ("en", ("en", "")),
        ("", ("en", "us")),
    ],
)
def test_split_locale(locale, expected):
    assert internet_search._split_locale(locale) == expected


def test_a_keyed_engine_without_a_key_does_not_fall_back_to_duckduckgo():
    bot = bot_with("tavily")
    bot.agent.tools[0].search_api_config = None
    tool = internet_search.create_internet_search_tool(bot)
    with patch.object(internet_search, "_search_with_duckduckgo_standalone") as ddg:
        result = tool(query="q")

    assert result["status"] == "error"
    ddg.assert_not_called()


def test_firecrawl_errors_reach_the_model_without_another_engine():
    tool = internet_search.create_internet_search_tool(bot_with("firecrawl"))
    with patch.object(
        internet_search.requests, "request", return_value=failing(402)
    ), patch.object(internet_search, "_search_with_duckduckgo_standalone") as ddg:
        result = tool(query="q")

    assert result == {
        "status": "error",
        "content": [
            {"text": "The internet search failed: Firecrawl search returned HTTP 402."}
        ],
    }
    ddg.assert_not_called()


def test_firecrawl_summarizes_every_page_in_order():
    pages = [
        {"title": f"T{i}", "url": f"https://{i}", "markdown": f"page {i}"}
        for i in range(10)
    ] + [{"title": "", "markdown": ""}]
    response = MagicMock(ok=True, status_code=200)
    response.json.return_value = {"success": True, "data": pages}
    with patch.object(
        internet_search.requests, "request", return_value=response
    ) as request, patch.object(
        internet_search,
        "_summarize_content_standalone",
        side_effect=lambda content, title, url, query: f"summary of {content}",
    ):
        results = internet_search._search_with_firecrawl_standalone(
            "q", API_KEY, "en-us", 10
        )

    # Empty pages are dropped, and the summaries keep the page order.
    assert [r["source_link"] for r in results] == [f"https://{i}" for i in range(10)]
    assert results[3]["content"] == "summary of page 3"
    kwargs = request.call_args.kwargs
    assert kwargs["json"]["limit"] == 10 and kwargs["json"]["country"] == "us"
    # A stuck connection cannot hold the chat until the Lambda times out.
    assert kwargs["timeout"] == internet_search._FIRECRAWL_TIMEOUT


def test_firecrawl_summaries_count_as_chat_cost():
    response = {
        "output": {"message": {"content": [{"text": "summary"}]}},
        "usage": {"inputTokens": 1000, "outputTokens": 100},
    }
    with patch.object(
        internet_search, "call_converse_api", return_value=response
    ), patch.object(internet_search, "emit_chat_cost") as emit:
        summary = internet_search._summarize_content_standalone(
            "page", "T", "https://t", "q"
        )

    assert summary == "summary"
    assert emit.call_args.args[0] > 0


def test_duckduckgo_uses_the_snippets_without_model_calls():
    ddgs = MagicMock()
    ddgs.__enter__.return_value.text.return_value = [
        {"title": "D", "href": "https://d", "body": "snippet"}
    ]
    with patch("duckduckgo_search.DDGS", return_value=ddgs), patch.object(
        internet_search, "_summarize_content_standalone"
    ) as summarize:
        results = internet_search._search_with_duckduckgo_standalone("q", "", "en")

    summarize.assert_not_called()
    assert results == [
        {"content": "snippet", "source_name": "D", "source_link": "https://d"}
    ]
    kwargs = ddgs.__enter__.return_value.text.call_args.kwargs
    assert kwargs["region"] == "wt-wt" and kwargs["timelimit"] is None
    # The "api" backend is deprecated.
    assert "backend" not in kwargs


def test_duckduckgo_regions_are_country_then_language():
    ddgs = MagicMock()
    ddgs.__enter__.return_value.text.return_value = []
    with patch("duckduckgo_search.DDGS", return_value=ddgs):
        internet_search._search_with_duckduckgo_standalone("q", "w", "ko-kr")

    kwargs = ddgs.__enter__.return_value.text.call_args.kwargs
    assert kwargs["region"] == "kr-ko" and kwargs["timelimit"] == "w"


def test_an_empty_summary_falls_back_to_the_page():
    # Models that always reason can use up the output limit before answering.
    response = {
        "output": {"message": {"content": [{"reasoningContent": {}}]}},
        "stopReason": "max_tokens",
        "usage": {},
    }
    with patch.object(
        internet_search, "call_converse_api", return_value=response
    ) as converse, patch.object(internet_search, "emit_chat_cost"):
        summary = internet_search._summarize_content_standalone(
            "page text", "T", "https://t", "q"
        )

    assert summary == "page text"
    # The chat stream has no API Gateway timeout, so throttling is retried.
    assert converse.call_args.kwargs["max_attempts"] > 1


@pytest.mark.parametrize(
    "error, reason",
    [
        ("RatelimitException", "rate limited"),
        ("TimeoutException", "timed out"),
        ("DuckDuckGoSearchException", "failed"),
    ],
)
def test_duckduckgo_errors_tell_the_model_why(error, reason):
    from duckduckgo_search import exceptions

    ddgs = MagicMock()
    ddgs.__enter__.return_value.text.side_effect = getattr(exceptions, error)("x")
    with patch("duckduckgo_search.DDGS", return_value=ddgs):
        with pytest.raises(internet_search.SearchApiError, match=reason):
            internet_search._search_with_duckduckgo_standalone("q", "", "en")


@pytest.mark.parametrize(
    "url, link",
    [
        ("https://example.com/a", "https://example.com/a"),
        ("http://example.com", "http://example.com"),
        # Would be presigned with the backend's permissions when shown.
        ("s3://other-bucket/key", ""),
        ("javascript:alert(1)", ""),
        ("", ""),
    ],
)
def test_only_web_links_are_kept(url, link):
    assert internet_search._web_link(url) == link


def search_with_agentcore(results=None, error=None, **kwargs):
    client = MagicMock()
    if error is not None:
        client.invoke_web_search.side_effect = error
    else:
        client.invoke_web_search.return_value = {"results": results or []}
    tool = internet_search.create_internet_search_tool(
        bot_with("agentcore", keyed=False)
    )
    with patch.object(internet_search, "get_web_search_client", return_value=client):
        return tool(**kwargs), client


def test_agentcore_web_search_needs_no_key():
    result, client = search_with_agentcore(
        [
            {"text": "sunny", "title": "T", "url": "https://t"},
            # Title and URL are optional in the response.
            {"text": "rain"},
        ],
        query="weather",
        time_limit="w",
    )

    request = client.invoke_web_search.call_args.kwargs
    assert request["webSearchId"] == "web-search.v1"
    assert request["searchQuery"] == "weather"
    after = request["filters"]["publishedDateFilter"]["publishedAfter"]
    age = datetime.now(timezone.utc) - after
    assert timedelta(days=7) <= age < timedelta(days=7, minutes=1)
    assert result["content"] == [
        {"json": {"content": "sunny", "source_name": "T", "source_link": "https://t"}},
        {"json": {"content": "rain", "source_name": "", "source_link": ""}},
    ]


def test_agentcore_web_search_tells_the_model_the_publication_time():
    published = datetime(2026, 11, 1, tzinfo=timezone.utc)
    result, _ = search_with_agentcore(
        [{"text": "news", "url": "https://n", "publishedAt": published}],
        query="news",
    )
    assert result["content"][0]["json"]["published_at"] == published.isoformat()


def test_agentcore_web_search_counts_as_chat_cost():
    with patch.object(internet_search, "emit_chat_cost") as emit:
        search_with_agentcore(query="weather")
    emit.assert_called_once_with(internet_search.WEB_SEARCH_PRICE_PER_QUERY)


def test_searches_all_pages_unless_the_model_asks_for_recent_ones():
    # A default time limit would drop the undated pages that answer most questions.
    _, client = search_with_agentcore(query="what is a cache")
    assert "filters" not in client.invoke_web_search.call_args.kwargs


def test_agentcore_web_search_tells_the_model_to_shorten_a_long_query():
    result, client = search_with_agentcore(query="q" * 201)
    client.invoke_web_search.assert_not_called()
    assert result["status"] == "error"
    assert "200 characters" in result["content"][0]["text"]


def test_failed_searches_raise_the_alarm_metric():
    # The model answers without the search, so only the metric shows a failure
    # such as an exhausted plan or an unsupported Region.
    from botocore.exceptions import EndpointConnectionError

    with patch.object(internet_search, "emit_metric") as emit:
        result, _ = search_with_agentcore(
            error=EndpointConnectionError(endpoint_url="https://x"), query="weather"
        )
    assert result["status"] == "error"
    emit.assert_called_once_with("InternetSearchFailures", 1)


def test_agentcore_web_search_errors_name_only_the_code():
    from botocore.exceptions import ClientError

    error = ClientError(
        {"Error": {"Code": "AccessDeniedException", "Message": "secret detail"}},
        "InvokeWebSearch",
    )
    result, _ = search_with_agentcore(error=error, query="weather")
    text = result["content"][0]["text"]
    assert "AccessDeniedException" in text and "secret detail" not in text
