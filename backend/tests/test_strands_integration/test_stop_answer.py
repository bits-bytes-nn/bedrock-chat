"""Stopping an answer keeps the text that was streamed."""

import asyncio
import threading
from unittest.mock import MagicMock, patch

from app.strands_integration import chat_strands
from strands import Agent
from strands.agent import NullConversationManager
from strands.models.model import Model


class StreamingModel(Model):
    """Streams the words one by one."""

    def __init__(self, words: list[str], first_delay: float = 0.0):
        self.words = words
        self.first_delay = first_delay

    def update_config(self, **model_config):
        pass

    def get_config(self):
        return {}

    def structured_output(self, *args, **kwargs):
        raise NotImplementedError

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs):
        yield {"messageStart": {"role": "assistant"}}
        # Time to the first token.
        await asyncio.sleep(self.first_delay)
        yield {"contentBlockStart": {"start": {}}}
        for word in self.words:
            # Slow enough for the stop watcher to look in between.
            await asyncio.sleep(0.02)
            yield {"contentBlockDelta": {"delta": {"text": word}}}
        yield {"contentBlockStop": {}}
        yield {"messageStop": {"stopReason": "end_turn"}}
        yield {
            "metadata": {
                "usage": {"inputTokens": 5, "outputTokens": 9, "totalTokens": 14},
                "metrics": {"latencyMs": 1},
            }
        }


def answer(words: list[str], should_stop=None, first_delay: float = 0.0):
    agent = Agent(
        model=StreamingModel(words, first_delay),
        callback_handler=None,
        conversation_manager=NullConversationManager(),
    )
    chat_input = MagicMock()
    chat_input.message.model = "claude-v5.5-haiku"
    streamed: list[str] = []
    with (
        patch.object(chat_strands, "STOP_CHECK_INTERVAL_SECONDS", 0.01),
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
    words = [f"w{i} " for i in range(40)]
    asked = threading.Event()
    # The user asks to stop while the words stream.
    threading.Timer(0.15, asked.set).start()

    result, streamed = answer(words, asked.is_set)

    assert result["stop_reason"] == "cancelled"
    body = result["message"].content[0].body
    # The stored answer is the text that the user saw.
    assert body == "".join(streamed) and body.startswith("w0 ")
    assert 0 < len(streamed) < len(words)


def test_an_answer_stopped_before_any_text_says_so():
    result, streamed = answer(["late"], lambda: True, first_delay=0.5)

    assert result["stop_reason"] == "cancelled"
    assert streamed == []
    assert result["message"].content[0].body == chat_strands.STOPPED_BEFORE_TEXT


def test_an_answer_without_a_stop_request_is_whole():
    result, _ = answer(["One ", "two"], lambda: False)

    assert result["stop_reason"] == "end_turn"
    assert result["message"].content[0].body == "One two"


def test_the_bedrock_stream_sees_the_stop_signal():
    # Strands clears its own cancel signal when a stopped answer ends, so a stream
    # that only had that one was read and billed to the end.
    import threading

    from app.strands_integration.agent.factory import StoppableBedrockModel
    from strands.models import BedrockModel

    seen: list = []

    async def fake_stream(self, *args, cancel_signal=None, **kwargs):
        seen.append(cancel_signal)
        yield {"messageStart": {"role": "assistant"}}

    model = StoppableBedrockModel.__new__(StoppableBedrockModel)
    model.stop_signal = threading.Event()
    agents_own = threading.Event()
    with patch.object(BedrockModel, "stream", fake_stream):

        async def consume():
            async for _ in model.stream([], cancel_signal=agents_own):
                pass

        asyncio.run(consume())

    assert seen == [model.stop_signal]
