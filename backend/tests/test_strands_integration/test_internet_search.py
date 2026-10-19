"""The search API requests and the results that the model gets."""

from unittest.mock import MagicMock, patch

import pytest
import requests
from app.repositories.models.custom_bot import InternetToolModel
from app.strands_integration.tools import internet_search

API_KEY = "test-api-key"


def bot_with(engine: str) -> MagicMock:
    tool = InternetToolModel.model_construct(
        tool_type="internet",
        name="internet_search",
        description="",
        search_engine=engine,
        search_api_config=MagicMock(api_key=API_KEY, max_results=3),
    )
    return MagicMock(agent=MagicMock(tools=[tool]))


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
    with patch("firecrawl.FirecrawlApp") as app, patch.object(
        internet_search, "_search_with_duckduckgo_standalone"
    ) as ddg:
        app.return_value.search.side_effect = RuntimeError("quota")
        result = tool(query="q")

    assert result["status"] == "error"
    ddg.assert_not_called()


def test_firecrawl_summarizes_every_page_in_order():
    pages = [
        {"title": f"T{i}", "url": f"https://{i}", "markdown": f"page {i}"}
        for i in range(10)
    ] + [{"title": "", "markdown": ""}]
    with patch("firecrawl.FirecrawlApp") as app, patch.object(
        internet_search,
        "_summarize_content_standalone",
        side_effect=lambda content, title, url, query: f"summary of {content}",
    ):
        app.return_value.search.return_value = MagicMock(data=pages)
        results = internet_search._search_with_firecrawl_standalone(
            "q", API_KEY, "en-us", 10
        )

    # Empty pages are dropped, and the summaries keep the page order.
    assert [r["source_link"] for r in results] == [f"https://{i}" for i in range(10)]
    assert results[3]["content"] == "summary of page 3"


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


def test_duckduckgo_regions_are_country_then_language():
    ddgs = MagicMock()
    ddgs.__enter__.return_value.text.return_value = []
    with patch("duckduckgo_search.DDGS", return_value=ddgs):
        internet_search._search_with_duckduckgo_standalone("q", "w", "ko-kr")

    kwargs = ddgs.__enter__.return_value.text.call_args.kwargs
    assert kwargs["region"] == "kr-ko" and kwargs["timelimit"] == "w"
