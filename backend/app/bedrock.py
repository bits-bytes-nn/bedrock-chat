from __future__ import annotations

import functools
import logging
import os
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    NotRequired,
    TypedDict,
)

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from app.config import DEFAULT_GENERATION_CONFIG
from app.model_registry import get_model_spec
from app.repositories.models.custom_bot import GenerationParamsModel
from app.repositories.models.custom_bot_guardrails import BedrockGuardrailsModel
from app.routes.schemas.conversation import type_model_name
from app.utils import get_bedrock_runtime_client

if TYPE_CHECKING:
    from mypy_boto3_bedrock_runtime.type_defs import (
        ConverseResponseTypeDef,
        ConverseStreamRequestTypeDef,
    )


logger = logging.getLogger(__name__)

BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "us-east-1")
ENABLE_BEDROCK_GLOBAL_INFERENCE = (
    os.environ.get("ENABLE_BEDROCK_GLOBAL_INFERENCE", "false") == "true"
)
ENABLE_BEDROCK_CROSS_REGION_INFERENCE = (
    os.environ.get("ENABLE_BEDROCK_CROSS_REGION_INFERENCE", "false") == "true"
)


def is_nova_model(model: type_model_name) -> bool:
    """Check if the model is an Amazon Nova model"""
    return get_model_spec(model).provider == "amazon"


def is_tooluse_supported(model: type_model_name) -> bool:
    return get_model_spec(model).supports_tool_use


def is_prefill_supported(model: type_model_name) -> bool:
    return get_model_spec(model).supports_prefill


def is_prompt_caching_supported(
    model: type_model_name, target: Literal["system", "message", "tool"]
) -> bool:
    return target in get_model_spec(model).prompt_caching


def is_unsigned_reasoning_content_supported(model: type_model_name) -> bool:
    return get_model_spec(model).accepts_unsigned_reasoning


class InferenceConfiguration(TypedDict):
    maxTokens: NotRequired[int]
    temperature: NotRequired[float]
    topP: NotRequired[float]
    stopSequences: NotRequired[list[str]]


class GuardrailConfiguration(TypedDict):
    guardrailIdentifier: str
    guardrailVersion: str
    trace: NotRequired[Literal["disabled", "enabled", "enabled_full"]]
    streamProcessingMode: NotRequired[Literal["async", "sync"]]


class ConverseConfiguration(TypedDict):
    inferenceConfig: InferenceConfiguration
    guardrailConfig: NotRequired[GuardrailConfiguration]
    additionalModelRequestFields: NotRequired[dict[str, Any]]


def generation_params_to_converse_configuration(
    model: type_model_name,
    generation_params: GenerationParamsModel | None = None,
    guardrail: BedrockGuardrailsModel | None = None,
    stream: bool = True,
    enable_reasoning: bool = False,
) -> ConverseConfiguration:
    """Build the Converse inference configuration, sending only the parameters that
    the model accepts."""
    spec = get_model_spec(model)
    defaults = spec.defaults

    def param(name: str) -> Any:
        if generation_params is not None:
            return getattr(generation_params, name)
        return defaults.get(name)

    max_tokens: int = (
        generation_params.max_tokens if generation_params else spec.default_max_tokens
    )
    inference_config: InferenceConfiguration = {}
    additional_fields: dict[str, Any] = {}

    thinking = enable_reasoning and spec.reasoning in ("budget", "adaptive")
    if thinking and spec.reasoning == "adaptive":
        additional_fields["thinking"] = {"type": "adaptive"}
    elif thinking:
        budget_tokens = (
            generation_params.reasoning_params.budget_tokens
            if generation_params and generation_params.reasoning_params
            else DEFAULT_GENERATION_CONFIG["reasoning_params"]["budget_tokens"]  # type: ignore[index]
        )
        if max_tokens <= budget_tokens:
            logger.warning(
                "max_tokens (%d) must be greater than budget_tokens (%d). Using %d.",
                max_tokens,
                budget_tokens,
                budget_tokens + 1024,
            )
            max_tokens = budget_tokens + 1024
        additional_fields["thinking"] = {
            "type": "enabled",
            "budget_tokens": budget_tokens,
        }

    inference_config["maxTokens"] = max_tokens

    if spec.supports_temperature:
        # Extended thinking requires temperature 1.0.
        inference_config["temperature"] = 1.0 if thinking else param("temperature")

    if spec.supports_top_p:
        inference_config["topP"] = param("top_p")

    stop_sequences = param("stop_sequences")
    if not (stop_sequences and any(stop_sequences)):
        stop_sequences = defaults.get("stop_sequences", [])
    if spec.supports_stop_sequences and stop_sequences:
        inference_config["stopSequences"] = stop_sequences

    top_k = param("top_k")
    # top_k cannot be used with extended thinking.
    if spec.top_k_field is not None and top_k is not None and not thinking:
        if spec.top_k_field == "claude":
            additional_fields["top_k"] = top_k
        else:
            # Amazon Nova returns an unexpected error if topK exceeds 128.
            additional_fields["inferenceConfig"] = {"topK": min(top_k, 128)}

    if spec.exclusive_temperature_top_p:
        # Keep top_p only when the user changed it and left temperature at the default.
        if (
            inference_config.get("temperature")
            == DEFAULT_GENERATION_CONFIG["temperature"]
            and inference_config.get("topP") != DEFAULT_GENERATION_CONFIG["top_p"]
        ):
            inference_config.pop("temperature", None)
        else:
            inference_config.pop("topP", None)

    converse_configuration: ConverseConfiguration = {
        "inferenceConfig": inference_config,
    }
    if additional_fields:
        converse_configuration["additionalModelRequestFields"] = additional_fields

    if guardrail and guardrail.guardrail_arn and guardrail.guardrail_version:
        converse_configuration["guardrailConfig"] = {
            "guardrailIdentifier": guardrail.guardrail_arn,
            "guardrailVersion": guardrail.guardrail_version,
            "trace": "enabled",
        }

        if stream:
            # https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-streaming.html
            converse_configuration["guardrailConfig"]["streamProcessingMode"] = "async"

    return converse_configuration


def get_text_from_converse_response(response: ConverseResponseTypeDef) -> str:
    """Return the first text block. Reasoning models may put a reasoning block first."""
    message = response["output"].get("message")
    if message is None:
        return ""
    return next((block["text"] for block in message["content"] if "text" in block), "")


def call_converse_api(
    args: ConverseStreamRequestTypeDef,
) -> ConverseResponseTypeDef:
    # Retries are handled by the client configuration.
    return get_bedrock_runtime_client().converse(**args)


def calculate_price(
    model: type_model_name,
    input_tokens: int,
    output_tokens: int,
    cache_read_input_tokens: int,
    cache_write_input_tokens: int,
) -> float:
    """Estimate the price in USD from the token usage."""
    price = get_model_spec(model).price

    cache_read_price = (
        price.cache_read_input if price.cache_read_input is not None else price.input
    )
    cache_write_price = (
        price.cache_write_input if price.cache_write_input is not None else price.input
    )
    return (
        input_tokens * price.input
        + output_tokens * price.output
        + cache_read_input_tokens * cache_read_price
        + cache_write_input_tokens * cache_write_price
    ) / 1000.0


@functools.cache
def _list_system_inference_profile_ids(region: str) -> frozenset[str]:
    """Return the IDs of the system-defined inference profiles in the region."""
    client = boto3.client(
        "bedrock",
        region_name=region,
        config=Config(
            connect_timeout=3,
            read_timeout=5,
            retries={"mode": "standard", "max_attempts": 3},
        ),
    )
    profile_ids: set[str] = set()
    kwargs: dict[str, Any] = {"typeEquals": "SYSTEM_DEFINED"}
    while True:
        response = client.list_inference_profiles(**kwargs)
        profile_ids.update(
            profile["inferenceProfileId"]
            for profile in response["inferenceProfileSummaries"]
        )
        if "nextToken" not in response:
            return frozenset(profile_ids)
        kwargs["nextToken"] = response["nextToken"]


def get_model_id(
    model: type_model_name,
    enable_global: bool = ENABLE_BEDROCK_GLOBAL_INFERENCE,
    enable_cross_region: bool = ENABLE_BEDROCK_CROSS_REGION_INFERENCE,
    bedrock_region: str = BEDROCK_REGION,
) -> str:
    """Resolve the model ID to invoke, preferring global, then geographic
    cross-Region inference profiles that exist in the region.

    Raises:
        ValueError: If the model is retired or unknown.
    """
    base_model_id = get_model_spec(model).bedrock_id
    if not (enable_global or enable_cross_region):
        return base_model_id

    global_profile_id = f"global.{base_model_id}"
    try:
        profile_ids = _list_system_inference_profile_ids(bedrock_region)
    except (BotoCoreError, ClientError):
        # Most current models are offered through a global profile, so try it rather
        # than failing every request while the lookup is unavailable.
        logger.warning(
            "Failed to list inference profiles in %s", bedrock_region, exc_info=True
        )
        return global_profile_id if enable_global else base_model_id

    if enable_global and global_profile_id in profile_ids:
        return global_profile_id

    if enable_cross_region:
        # Geographic profiles are named "<geo>.<base model id>", for example "us." or "apac.".
        regional_profile_ids = sorted(
            profile_id
            for profile_id in profile_ids
            if profile_id.split(".", 1)[-1] == base_model_id
            and profile_id != global_profile_id
        )
        if regional_profile_ids:
            return regional_profile_ids[0]

    logger.warning(
        "No inference profile for %s in %s. Using the base model ID, which only works "
        "if the model supports on-demand throughput in this region.",
        model,
        bedrock_region,
    )
    return base_model_id
