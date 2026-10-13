"""
Agent factory for Strands integration.
"""

import logging
import os

from botocore.config import Config

from app.repositories.models.conversation import type_model_name
from app.repositories.models.custom_bot import BotModel, GenerationParamsModel
from app.repositories.models.custom_bot_guardrails import BedrockGuardrailsModel
from app.strands_integration.utils import get_strands_tools
from strands import Agent
from strands.agent import NullConversationManager
from strands.hooks import HookCallback, HookProvider
from strands.models import BedrockModel

from app.strands_integration.agent.config import get_bedrock_model_config

logger = logging.getLogger(__name__)

BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "us-east-1")
# botocore retries throttling and transient errors before the stream starts. The
# Strands retry is disabled because it also retries a stream that was cut off midway,
# which would send the tokens that the user already received again.
BEDROCK_CLIENT_CONFIG = Config(
    connect_timeout=5,
    read_timeout=120,
    retries={"mode": "standard", "max_attempts": 3},
)


def create_strands_agent(
    bot: BotModel | None,
    instructions: list[str],
    model_name: type_model_name,
    generation_params: GenerationParamsModel | None = None,
    guardrail: BedrockGuardrailsModel | None = None,
    enable_reasoning: bool = False,
    prompt_caching_enabled: bool = False,
    has_tools: bool = False,
    hooks: list[HookProvider] | None = None,
) -> Agent:
    model_config = get_bedrock_model_config(
        model_name=model_name,
        instructions=instructions,
        generation_params=generation_params,
        guardrail=guardrail,
        enable_reasoning=enable_reasoning,
        prompt_caching_enabled=prompt_caching_enabled,
        has_tools=has_tools,
    )
    logger.debug(f"[AGENT_FACTORY] Model config: {model_config}")
    model = BedrockModel(
        region_name=BEDROCK_REGION,
        boto_client_config=BEDROCK_CLIENT_CONFIG,
        **model_config,
    )

    # Strands does not support list of instructions, so we join them into a single string.
    system_prompt = "\n\n".join(instructions).strip() if instructions else None

    agent_hooks: list[HookProvider | HookCallback] = list(hooks or [])
    agent = Agent(
        model=model,
        tools=get_strands_tools(bot, model_name),  # type: ignore
        hooks=agent_hooks,
        system_prompt=system_prompt,
        retry_strategy=None,
        # The default manager drops the oldest messages when the context overflows,
        # which silently loses context; the error is reported as input_too_long.
        conversation_manager=NullConversationManager(),
    )
    return agent
