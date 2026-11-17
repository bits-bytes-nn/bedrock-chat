"""The limit on the model calls of one answer, and the cost of failed answers."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from app.strands_integration import chat_strands
from app.strands_integration.handlers.model_call_limit import ModelCallLimit


def test_the_answer_ends_with_a_note_after_the_limit():
    limit = ModelCallLimit(max_calls=2)
    events = [SimpleNamespace(cancel=False) for _ in range(3)]
    for event in events:
        limit.before_model_call(event)

    assert [bool(e.cancel) for e in events] == [False, False, True]
    assert "2 steps" in events[2].cancel


def test_a_failed_answer_still_counts_its_cost():
    agent = MagicMock(tool_names=[])
    agent.side_effect = RuntimeError("throttled on the third tool round trip")
    agent.event_loop_metrics.accumulated_usage = {
        "inputTokens": 100_000,
        "outputTokens": 1_000,
    }
    chat_input = MagicMock()
    chat_input.message.model = "claude-v5.5-haiku"
    with (
        patch.object(chat_strands, "create_strands_agent", return_value=agent),
        patch.object(chat_strands, "simple_message_models_to_strands_messages"),
        patch.object(chat_strands, "emit_chat_cost") as emit,
    ):
        with pytest.raises(RuntimeError):
            chat_strands.converse_with_strands(
                bot=None,
                chat_input=chat_input,
                instructions=[],
                generation_params=None,
                guardrail=None,
                display_citation=False,
                messages=[],
                search_results=[],
            )

    assert emit.call_args.args[0] > 0


def test_a_model_that_keeps_calling_tools_is_stopped():
    from strands import Agent, tool
    from strands.models.model import Model

    class ToolLoopModel(Model):
        calls = 0

        def update_config(self, **model_config):
            pass

        def get_config(self):
            return {}

        def structured_output(self, *args, **kwargs):
            raise NotImplementedError

        async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs):
            ToolLoopModel.calls += 1
            tool_use_id = f"t{ToolLoopModel.calls}"
            yield {"messageStart": {"role": "assistant"}}
            yield {
                "contentBlockStart": {
                    "start": {"toolUse": {"toolUseId": tool_use_id, "name": "lookup"}}
                }
            }
            yield {"contentBlockDelta": {"delta": {"toolUse": {"input": "{}"}}}}
            yield {"contentBlockStop": {}}
            yield {"messageStop": {"stopReason": "tool_use"}}
            yield {
                "metadata": {
                    "usage": {"inputTokens": 10, "outputTokens": 1, "totalTokens": 11},
                    "metrics": {"latencyMs": 1},
                }
            }

    @tool
    def lookup() -> str:
        """Look something up."""
        return "nothing"

    agent = Agent(
        model=ToolLoopModel(),
        tools=[lookup],
        hooks=[ModelCallLimit(max_calls=3)],
        callback_handler=None,
    )
    result = agent("question")

    assert ToolLoopModel.calls == 3
    assert result.stop_reason == "end_turn"
    assert "3 steps" in result.message["content"][0]["text"]
