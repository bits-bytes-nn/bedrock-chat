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


@pytest.mark.parametrize("engine", ["tavily", "brave"])
def test_a_failed_request_is_a_tool_error_without_the_query(engine, caplog):
    response = MagicMock(ok=False, status_code=429)
    tool = internet_search.create_internet_search_tool(bot_with(engine))
    with patch.object(internet_search.requests, "request", return_value=response):
        result = tool(query="private words")
    with patch.object(
        internet_search.requests,
        "request",
        side_effect=requests.ConnectionError("https://x/?q=private words"),
    ):
        failed_connection = tool(query="private words")

    for failure in (result, failed_connection):
        assert failure["status"] == "error"
    assert "HTTP 429" in caplog.text
    # The request URL holds the query.
    assert "private words" not in caplog.text
