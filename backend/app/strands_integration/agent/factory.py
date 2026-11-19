"""
Agent factory for Strands integration.
"""

import logging
import os
import threading
from typing import Any, AsyncGenerator

import boto3
from botocore.config import Config

from app.repositories.models.conversation import type_model_name
from app.repositories.models.custom_bot import BotModel, GenerationParamsModel
from app.repositories.models.custom_bot_guardrails import BedrockGuardrailsModel
from app.strands_integration.utils import get_strands_tools
from strands import Agent
from strands.agent import NullConversationManager
from strands.hooks import HookCallback, HookProvider
from strands.models import BedrockModel

from app.strands_integration.agent.config import (
    get_bedrock_model_config,
    get_system_prompt,
)

logger = logging.getLogger(__name__)


class StoppableBedrockModel(BedrockModel):
    """Closes its Bedrock stream when `stop_signal` is set.

    Strands passes the agent's own cancel signal to the stream, and clears it when
    the cancelled invocation ends; a stream that has not looked at it by then is
    read, generated and billed to the end (strands-agents 1.59). The caller's
    signal stays set.
    """

    stop_signal: threading.Event | None = None

    async def stream(  # type: ignore[override]
        self, *args: Any, cancel_signal: threading.Event | None = None, **kwargs: Any
    ) -> AsyncGenerator[Any, None]:
        async for event in super().stream(
            *args, cancel_signal=self.stop_signal or cancel_signal, **kwargs
        ):
            yield event


BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "us-east-1")
# botocore retries throttling and transient errors before the stream starts. The
# Strands retry is disabled because it also retries a stream that was cut off midway,
# which would send the tokens that the user already received again.
BEDROCK_CLIENT_CONFIG = Config(
    connect_timeout=5,
    read_timeout=120,
    retries={"mode": "standard", "max_attempts": 3},
)
# One session per Lambda container: creating one costs tens of milliseconds a chat.
BEDROCK_SESSION = boto3.Session(region_name=BEDROCK_REGION)


def create_strands_agent(
    bot: BotModel | None,
    instructions: list[str],
    model_name: type_model_name,
    generation_params: GenerationParamsModel | None = None,
    guardrail: BedrockGuardrailsModel | None = None,
    enable_reasoning: bool = False,
    prompt_caching_enabled: bool = False,
    hooks: list[HookProvider] | None = None,
) -> Agent:
    tools = get_strands_tools(bot, model_name)
    model_config = get_bedrock_model_config(
        model_name=model_name,
        generation_params=generation_params,
        guardrail=guardrail,
        enable_reasoning=enable_reasoning,
        prompt_caching_enabled=prompt_caching_enabled,
    )
    logger.debug(f"[AGENT_FACTORY] Model config: {model_config}")
    model = StoppableBedrockModel(
        boto_session=BEDROCK_SESSION,
        boto_client_config=BEDROCK_CLIENT_CONFIG,
        **model_config,
    )

    system_prompt = get_system_prompt(
        instructions, model_name, prompt_caching_enabled, has_tools=bool(tools)
    )

    agent_hooks: list[HookProvider | HookCallback] = list(hooks or [])
    agent = Agent(
        model=model,
        tools=tools,  # type: ignore
        hooks=agent_hooks,
        system_prompt=system_prompt,
        retry_strategy=None,
        # The default manager drops the oldest messages when the context overflows,
        # which silently loses context; the error is reported as input_too_long.
        # This also gives up its truncation of oversized tool results on overflow.
        conversation_manager=NullConversationManager(),
    )
    return agent
