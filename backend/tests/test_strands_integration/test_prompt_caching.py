"""Where the requests to Bedrock get their cache points."""

import warnings
from unittest.mock import patch

import pytest
from app.repositories.models.conversation import SimpleMessageModel, TextContentModel
from app.strands_integration.agent.factory import create_strands_agent
from app.strands_integration.converters.message_converter import (
    simple_message_models_to_strands_messages,
)
from app.usecases import global_config


def user(text: str) -> SimpleMessageModel:
    return SimpleMessageModel(
        role="user", content=[TextContentModel(content_type="text", body=text)]
    )


def assistant(text: str) -> SimpleMessageModel:
    return SimpleMessageModel(
        role="assistant", content=[TextContentModel(content_type="text", body=text)]
    )


HISTORY = [user("first"), assistant("answer"), user("second")]


def request(model: str, search_engine: str = "", caching: bool = True) -> dict:
    """The Converse request that the agent sends for HISTORY."""
    with patch.object(global_config, "DEFAULT_CHAT_SEARCH_ENGINE", search_engine):
        agent = create_strands_agent(
            bot=None,
            instructions=["Answer briefly."],
            model_name=model,
            prompt_caching_enabled=caching,
        )
    messages = simple_message_models_to_strands_messages(
        HISTORY,
        model=model,
        prompt_caching_enabled=caching,
        has_tools=bool(agent.tool_names),
    )
    return agent.model.format_request(
        messages,
        tool_specs=agent.tool_registry.get_all_tool_specs() or None,
        system_prompt_content=agent._system_prompt_content,
    )


def cache_points(blocks: list[dict]) -> int:
    return sum("cachePoint" in block for block in blocks)


def message_cache_points(req: dict) -> list[int]:
    return [cache_points(message["content"]) for message in req["messages"]]


def test_claude_gets_the_cache_points_of_strands_without_deprecated_options():
    with warnings.catch_warnings():
        warnings.filterwarnings("error", message=".*deprecated.*")
        req = request("claude-v5.5-haiku", search_engine="duckduckgo")

    assert cache_points(req["system"]) == 1
    assert "cachePoint" in req["toolConfig"]["tools"][-1]
    # Only the last user message, so the point moves forward with the tool results.
    assert message_cache_points(req) == [0, 0, 1]


def test_nova_gets_its_cache_points_from_the_application():
    req = request("amazon-nova-lite")

    assert cache_points(req["system"]) == 1
    assert message_cache_points(req) == [1, 0, 1]


def test_nova_with_tools_caches_no_system_prompt():
    # Nova cannot cache tool definitions.
    req = request("amazon-nova-lite", search_engine="duckduckgo")

    assert cache_points(req["system"]) == 0


@pytest.mark.parametrize("model", ["claude-v5.5-haiku", "amazon-nova-lite"])
def test_bots_with_caching_off_get_no_cache_points(model: str):
    req = request(model, search_engine="duckduckgo", caching=False)

    assert cache_points(req["system"]) == 0
    assert all(
        "cachePoint" not in tool for tool in req.get("toolConfig", {}).get("tools", [])
    )
    assert message_cache_points(req) == [0, 0, 0]
