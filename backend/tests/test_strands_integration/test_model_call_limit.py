"""The limit on the model calls of one answer, and the cost of failed answers."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from app.strands_integration import chat_strands
from app.strands_integration.handlers.model_call_limit import ModelCallLimit


def test_the_answer_ends_with_a_note_after_the_limit():
    from app.strands_integration.handlers import model_call_limit

    limit = ModelCallLimit(max_calls=2)
    events = [SimpleNamespace(cancel=False) for _ in range(3)]
    with patch.object(model_call_limit, "emit_metric") as emit:
        for event in events:
            limit.before_model_call(event)

    assert [bool(e.cancel) for e in events] == [False, False, True]
    assert "2 steps" in events[2].cancel
    emit.assert_called_once_with("ModelCallLimitReached", 1)


def test_a_failed_answer_still_counts_its_cost(caplog):
    import logging

    caplog.set_level(logging.INFO)
    agent = MagicMock(tool_names=[])
    agent.side_effect = RuntimeError("throttled on the third tool round trip")
    agent.event_loop_metrics.accumulated_usage = {
        "inputTokens": 100_000,
        "outputTokens": 1_000,
    }
    agent.event_loop_metrics.cycle_count = 3
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
    # Failed answers count in the latency and cost figures too.
    assert any(
        '"stop_reason": "error"' in r.getMessage()
        for r in caplog.records
        if "answer metrics" in r.getMessage()
    )


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


def test_every_answer_logs_its_latency_tokens_and_price(caplog):
    import json
    import logging

    agent = MagicMock(tool_names=[])

    def answer(_messages, cancel_signal=None):
        agent.callback_handler(data="Hi")
        return SimpleNamespace(
            stop_reason="end_turn",
            message={"role": "assistant", "content": [{"text": "Hi"}]},
            metrics=SimpleNamespace(
                cycle_count=1,
                accumulated_usage={
                    "inputTokens": 10,
                    "outputTokens": 2,
                    "cacheReadInputTokens": 0,
                    "cacheWriteInputTokens": 0,
                },
            ),
        )

    agent.side_effect = answer
    chat_input = MagicMock()
    chat_input.message.model = "claude-v5.5-haiku"
    with (
        patch.object(chat_strands, "create_strands_agent", return_value=agent),
        patch.object(chat_strands, "simple_message_models_to_strands_messages"),
        caplog.at_level(logging.INFO, logger=chat_strands.logger.name),
    ):
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

    line = next(r.getMessage() for r in caplog.records if "answer metrics" in r.message)
    metrics = json.loads(line.split("answer metrics: ", 1)[1])
    assert metrics["model"] == "claude-v5.5-haiku"
    assert isinstance(metrics["ttft_ms"], int)
    assert metrics["duration_ms"] >= metrics["ttft_ms"]
    assert (metrics["input"], metrics["output"], metrics["model_calls"]) == (10, 2, 1)
    assert metrics["usd_micros"] == round(metrics["price"] * 1_000_000)
