"""History sent to the model, with and without tools."""

from unittest.mock import MagicMock, patch

import pytest
from app.repositories.models.conversation import (
    SimpleMessageModel,
    TextContentModel,
    TextToolResultModel,
    ToolResultContentModel,
    ToolResultContentModelBody,
    ToolUseContentModel,
    ToolUseContentModelBody,
)
from app.repositories.models.custom_bot_guardrails import BedrockGuardrailsModel
from app.strands_integration import chat_strands
from app.strands_integration.converters.message_converter import (
    simple_message_models_to_strands_messages,
)


def text(role: str, body: str) -> SimpleMessageModel:
    return SimpleMessageModel(
        role=role, content=[TextContentModel(content_type="text", body=body)]
    )


# An answer that searched once, as trace_to_root returns it from the thinking log.
HISTORY = [
    text("user", "weather?"),
    SimpleMessageModel(
        role="assistant",
        content=[
            TextContentModel(content_type="text", body="Searching."),
            ToolUseContentModel(
                content_type="toolUse",
                body=ToolUseContentModelBody(
                    tool_use_id="t1", name="internet_search", input={"query": "q"}
                ),
            ),
        ],
    ),
    SimpleMessageModel(
        role="user",
        content=[
            ToolResultContentModel(
                content_type="toolResult",
                body=ToolResultContentModelBody(
                    tool_use_id="t1",
                    content=[TextToolResultModel(text="sunny")],
                    status="success",
                ),
            )
        ],
    ),
    text("assistant", "It is sunny."),
    text("user", "thanks"),
]


@pytest.mark.parametrize(
    "has_tools, roles",
    [
        (True, ["user", "assistant", "user", "assistant", "user"]),
        # Bedrock rejects tool blocks without tools, so the tool steps are left out
        # and the roles still alternate.
        (False, ["user", "assistant", "user"]),
    ],
)
def test_tool_steps_are_sent_only_with_tools(has_tools, roles):
    messages = simple_message_models_to_strands_messages(
        HISTORY,
        model="claude-v5.5-haiku",
        prompt_caching_enabled=False,
        has_tools=has_tools,
    )

    assert [m["role"] for m in messages] == roles
    blocks = [block for m in messages for block in m["content"]]
    assert any("toolUse" in block for block in blocks) == has_tools


class Stop(Exception):
    pass


def test_the_chat_drops_tool_steps_when_the_agent_has_no_tools():
    with patch.object(
        chat_strands, "create_strands_agent", return_value=MagicMock(tool_names=[])
    ), patch.object(
        chat_strands, "simple_message_models_to_strands_messages", side_effect=Stop
    ) as convert, pytest.raises(
        Stop
    ):
        chat_strands.converse_with_strands(
            bot=None,
            chat_input=MagicMock(),
            instructions=[],
            generation_params=None,
            guardrail=None,
            display_citation=False,
            messages=HISTORY,
            search_results=[],
        )

    assert convert.call_args.kwargs["has_tools"] is False


@pytest.mark.parametrize("grounding, relevance", [(0.7, 0.0), (0.0, 0.7)])
def test_only_the_question_of_this_turn_is_checked_for_grounding(grounding, relevance):
    guardrail = BedrockGuardrailsModel(
        is_guardrail_enabled=True,
        hate_threshold=0,
        insults_threshold=0,
        sexual_threshold=0,
        violence_threshold=0,
        misconduct_threshold=0,
        grounding_threshold=grounding,
        relevance_threshold=relevance,
        guardrail_arn="arn",
        guardrail_version="1",
    )
    result = {
        "bot_id": "b",
        "content": "It is sunny.",
        "source_name": "s",
        "source_link": "https://s",
        "rank": 0,
        "metadata": {},
        "page_number": None,
    }
    messages = simple_message_models_to_strands_messages(
        [text("user", "first"), text("assistant", "answer"), text("user", "second")],
        model="gpt-oss-120b",
        guardrail=guardrail,
        search_results=[result],
        has_tools=False,
    )

    assert [len(m["content"]) for m in messages] == [1, 1, 2]
    source, query = messages[-1]["content"]
    assert source["guardContent"]["text"]["qualifiers"] == ["grounding_source"]
    assert query["guardContent"]["text"] == {"text": "second", "qualifiers": ["query"]}
