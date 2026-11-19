"""
Main chat function for Strands integration.
"""

import json
import logging
import time
from typing import Callable

from app.stream import ToolRunResult
from app.bedrock import calculate_price, BedrockGuardrailsModel
from app.repositories.models.conversation import SimpleMessageModel
from app.repositories.models.custom_bot import (
    BotModel,
    GenerationParamsModel,
)
from app.routes.schemas.conversation import ChatInput, type_model_name
from app.strands_integration.agent import create_strands_agent
from app.strands_integration.converters import (
    simple_message_models_to_strands_messages,
    strands_message_to_simple_message_model,
    strands_message_to_message_model,
)
from app.metrics import emit_chat_cost
from app.strands_integration.handlers import (
    ModelCallLimit,
    ToolResultCapture,
    create_callback_handler,
)
from app.stream import OnStopInput, OnThinking
from app.utils import get_current_time
from app.vector_search import (
    SearchResult,
)

from strands import Agent
from strands.telemetry.metrics import EventLoopMetrics
from strands.types.event_loop import StopReason
from strands.types.content import Message
from strands.types.exceptions import MaxTokensReachedException

logger = logging.getLogger(__name__)


def converse_with_strands(
    bot: BotModel | None,
    chat_input: ChatInput,
    instructions: list[str],
    generation_params: GenerationParamsModel | None,
    guardrail: BedrockGuardrailsModel | None,
    display_citation: bool,
    messages: list[SimpleMessageModel],
    search_results: list[SearchResult],
    on_stream: Callable[[str], None] | None = None,
    on_thinking: Callable[[OnThinking], None] | None = None,
    on_tool_result: Callable[[ToolRunResult], None] | None = None,
    on_reasoning: Callable[[str], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> OnStopInput:
    """
    Chat with Strands agents.

    Architecture Overview:

    1. Reasoning Content:
       - Streaming: CallbackHandler processes reasoning events for real-time display.
       - Persistence: CallbackHandler notifies the message including reasoning content.

    2. Tool Use/Result (Thinking Log):
       - Streaming: ToolResultCapture processes tool events for real-time display.
       - Persistence: CallbackHandler notifies the message including tool use/result content.

    3. Related Documents (Citations):
       - Source: ToolResultCapture notifies related document.
       - Reason: Requires access to raw tool results for source_link extraction

    Why This Hybrid Approach:

    - ToolResultCapture: Processes raw tool results during execution hooks, enabling
      source_link extraction and citation functionality.

    - CallbackHandler: Captures all messages including reasoning / tool use/result content
      that may not be available in final AgentResult when tools are used.
    """

    tool_capture = ToolResultCapture(
        display_citation=display_citation,
        on_thinking=on_thinking,
        on_tool_result=on_tool_result,
    )

    prompt_caching_enabled = bot.prompt_caching_enabled if bot is not None else True

    agent = create_strands_agent(
        bot=bot,
        instructions=instructions,
        model_name=chat_input.message.model,
        generation_params=generation_params,
        guardrail=guardrail,
        enable_reasoning=chat_input.enable_reasoning,
        prompt_caching_enabled=prompt_caching_enabled,
        hooks=[tool_capture, ModelCallLimit()],
    )

    thinking_log: list[SimpleMessageModel] = []

    def on_message(message: Message):
        if any(
            "toolUse" in content or "toolResult" in content
            for content in message["content"]
        ):
            thinking_log.append(strands_message_to_simple_message_model(message))

    # The first streamed text or reasoning, for the time to first token, and the
    # streamed text, which is the answer when the user stops it.
    started = time.monotonic()
    first_output_at: list[float] = []
    streamed: list[str] = []

    def streaming(callback: Callable[[str], None] | None, is_text: bool):
        def wrapped(text: str):
            if not first_output_at:
                first_output_at.append(time.monotonic())
            if is_text:
                streamed.append(text)
            if callback:
                callback(text)
            # Strands stops at the next chunk and drops the message it was building.
            if should_stop and should_stop():
                agent.cancel()

        return wrapped

    agent.callback_handler = create_callback_handler(
        on_stream=streaming(on_stream, is_text=True),
        on_reasoning=streaming(on_reasoning, is_text=False),
        on_message=on_message,
    )

    # Convert SimpleMessageModel list to Strands Messages format
    strands_messages = simple_message_models_to_strands_messages(
        simple_messages=messages,
        model=chat_input.message.model,
        guardrail=guardrail,
        search_results=search_results,
        prompt_caching_enabled=prompt_caching_enabled,
        has_tools=bool(agent.tool_names),
    )

    def run_agent(agent: Agent) -> tuple[StopReason, Message, EventLoopMetrics]:
        try:
            result = agent(strands_messages)
            return (
                result.stop_reason,
                result.message,
                result.metrics,
            )

        except MaxTokensReachedException:
            return (
                "max_tokens",
                agent.messages[-1],
                agent.event_loop_metrics,
            )
        except Exception:
            # The model calls before the failure are billed, and the cost is
            # otherwise emitted only for a finished answer.
            emit_chat_cost(_price(chat_input.message.model, agent.event_loop_metrics))
            raise

    stop_reason, result_message, metrics = run_agent(agent)
    if stop_reason == "cancelled":
        # Keep what the user saw. The stopped model call reports no usage, so its
        # tokens are missing from the price.
        text = "".join(streamed)
        result_message = {
            "role": "assistant",
            "content": [{"text": text}] if text else [],
        }

    # Convert Strands Message to MessageModel
    message = strands_message_to_message_model(
        message=result_message,
        model_name=chat_input.message.model,
        create_time=get_current_time(),
        thinking_log=thinking_log,
    )

    # Extract token usage from metrics
    input_tokens = metrics.accumulated_usage.get("inputTokens", 0)
    output_tokens = metrics.accumulated_usage.get("outputTokens", 0)
    cache_read_input_tokens = metrics.accumulated_usage.get("cacheReadInputTokens", 0)
    cache_write_input_tokens = metrics.accumulated_usage.get("cacheWriteInputTokens", 0)

    price = _price(chat_input.message.model, metrics)

    # One line per answer, the source of the latency, token and cost figures
    # (docs/ADMINISTRATOR.md#answer-metrics).
    logger.info(
        "answer metrics: %s",
        json.dumps(
            {
                "model": chat_input.message.model,
                "stop_reason": stop_reason,
                "ttft_ms": (
                    round((first_output_at[0] - started) * 1000)
                    if first_output_at
                    else None
                ),
                "duration_ms": round((time.monotonic() - started) * 1000),
                "model_calls": metrics.cycle_count,
                "input": input_tokens,
                "output": output_tokens,
                "cache_read_input": cache_read_input_tokens,
                "cache_write_input": cache_write_input_tokens,
                "price": price,
            }
        ),
    )

    return OnStopInput(
        message=message,
        stop_reason=stop_reason,
        input_token_count=input_tokens,
        output_token_count=output_tokens,
        cache_read_input_count=cache_read_input_tokens,
        cache_write_input_count=cache_write_input_tokens,
        price=price,
    )


def _price(model: type_model_name, metrics: EventLoopMetrics) -> float:
    usage = metrics.accumulated_usage
    return calculate_price(
        model=model,
        input_tokens=usage.get("inputTokens", 0),
        output_tokens=usage.get("outputTokens", 0),
        cache_read_input_tokens=usage.get("cacheReadInputTokens", 0),
        cache_write_input_tokens=usage.get("cacheWriteInputTokens", 0),
    )
