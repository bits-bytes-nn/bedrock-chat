"""
Agent configuration utilities for Strands integration.
"""

import logging

from app.bedrock import (
    get_model_id,
    generation_params_to_converse_configuration,
    is_prompt_caching_automatic,
    is_prompt_caching_supported,
)
from app.repositories.models.conversation import type_model_name
from app.repositories.models.custom_bot import GenerationParamsModel
from app.repositories.models.custom_bot_guardrails import BedrockGuardrailsModel

from app.model_registry import CLAUDE_CACHE_TTL
from strands.models import BedrockModel, CacheConfig
from strands.types.content import SystemContentBlock

logger = logging.getLogger(__name__)


def get_system_prompt(
    instructions: list[str],
    model_name: type_model_name,
    prompt_caching_enabled: bool,
    has_tools: bool,
) -> list[SystemContentBlock] | None:
    """The instructions as one system block. Models whose cache points Strands does
    not place get one after it, unless they have tools that they cannot cache."""
    text = "\n\n".join(instructions).strip()
    if not text:
        return None
    blocks: list[SystemContentBlock] = [{"text": text}]
    if (
        prompt_caching_enabled
        and not is_prompt_caching_automatic(model_name)
        and is_prompt_caching_supported(model_name, target="system")
        and not (
            has_tools and not is_prompt_caching_supported(model_name, target="tool")
        )
    ):
        blocks.append({"cachePoint": {"type": "default"}})
    return blocks


def get_bedrock_model_config(
    model_name: type_model_name,
    generation_params: GenerationParamsModel | None = None,
    guardrail: BedrockGuardrailsModel | None = None,
    enable_reasoning: bool = False,
    prompt_caching_enabled: bool = False,
) -> BedrockModel.BedrockConfig:
    """Get Bedrock model configuration."""

    model_id = get_model_id(model_name)

    config: BedrockModel.BedrockConfig = {
        "model_id": model_id,
    }

    # Prepare model-specific parameters
    converse_config = generation_params_to_converse_configuration(
        model=model_name,
        generation_params=generation_params,
        guardrail=guardrail,
        enable_reasoning=enable_reasoning,
    )

    # Add model parameters if available
    inference_config = converse_config["inferenceConfig"]
    if "temperature" in inference_config:
        config["temperature"] = inference_config["temperature"]

    if "topP" in inference_config:
        config["top_p"] = inference_config["topP"]

    if "maxTokens" in inference_config:
        config["max_tokens"] = inference_config["maxTokens"]

    if "stopSequences" in inference_config:
        config["stop_sequences"] = inference_config["stopSequences"]

    # Add Guardrails configuration (Strands way)
    if "guardrailConfig" in converse_config:
        guardrail_config = converse_config["guardrailConfig"]
        config["guardrail_id"] = guardrail_config["guardrailIdentifier"]
        config["guardrail_version"] = guardrail_config["guardrailVersion"]

        if "trace" in guardrail_config:
            config["guardrail_trace"] = guardrail_config["trace"]

        if "streamProcessingMode" in guardrail_config:
            config["guardrail_stream_processing_mode"] = guardrail_config[
                "streamProcessingMode"
            ]

        logger.info(f"Enabled Guardrails: {guardrail_config["guardrailIdentifier"]}")

    # Other models get their cache points in get_system_prompt and the message converter.
    if prompt_caching_enabled and is_prompt_caching_automatic(model_name):
        config["cache_config"] = CacheConfig(
            strategy="anthropic", ttl=CLAUDE_CACHE_TTL, tools_ttl=True
        )

    if "additionalModelRequestFields" in converse_config:
        config["additional_request_fields"] = converse_config[
            "additionalModelRequestFields"
        ]

    return config
