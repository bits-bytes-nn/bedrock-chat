"""Stopping an answer keeps the text that was streamed."""

from unittest.mock import MagicMock, patch

from app.strands_integration import chat_strands
from strands import Agent
from strands.agent import NullConversationManager
from strands.models.model import Model


class StreamingModel(Model):
    """Streams the words one by one."""

    def __init__(self, words: list[str]):
        self.words = words

    def update_config(self, **model_config):
        pass

    def get_config(self):
        return {}

    def structured_output(self, *args, **kwargs):
        raise NotImplementedError

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs):
        yield {"messageStart": {"role": "assistant"}}
        yield {"contentBlockStart": {"start": {}}}
        for word in self.words:
            yield {"contentBlockDelta": {"delta": {"text": word}}}
        yield {"contentBlockStop": {}}
        yield {"messageStop": {"stopReason": "end_turn"}}
        yield {
            "metadata": {
                "usage": {"inputTokens": 5, "outputTokens": 9, "totalTokens": 14},
                "metrics": {"latencyMs": 1},
            }
        }


def answer(words: list[str], should_stop=None):
    agent = Agent(
        model=StreamingModel(words),
        callback_handler=None,
        conversation_manager=NullConversationManager(),
    )
    chat_input = MagicMock()
    chat_input.message.model = "claude-v5.5-haiku"
    streamed: list[str] = []
    with (
        patch.object(chat_strands, "create_strands_agent", return_value=agent),
        patch.object(
            chat_strands,
            "simple_message_models_to_strands_messages",
            return_value=[{"role": "user", "content": [{"text": "write"}]}],
        ),
    ):
        return (
            chat_strands.converse_with_strands(
                bot=None,
                chat_input=chat_input,
                instructions=[],
                generation_params=None,
                guardrail=None,
                display_citation=False,
                messages=[],
                search_results=[],
                on_stream=streamed.append,
                should_stop=should_stop,
            ),
            streamed,
        )


def test_a_stopped_answer_keeps_the_streamed_text():
    words = ["One ", "two ", "three ", "four ", "five"]
    asked = []

    def should_stop() -> bool:
        asked.append(True)
        return len(asked) >= 2

    result, streamed = answer(words, should_stop)

    assert result["stop_reason"] == "cancelled"
    body = result["message"].content[0].body
    # Strands stops at the next chunk after the request.
    assert body == "".join(streamed) and body.startswith("One two")
    assert len(streamed) < len(words)


def test_an_answer_without_a_stop_request_is_whole():
    result, _ = answer(["One ", "two"], lambda: False)

    assert result["stop_reason"] == "end_turn"
    assert result["message"].content[0].body == "One two"
