from __future__ import annotations

import functools
import logging
import os
import time
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Literal,
    NotRequired,
    TypedDict,
    TypeVar,
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

_T = TypeVar("_T")

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


def is_document_supported(model: type_model_name) -> bool:
    return get_model_spec(model).supports_documents


def is_prompt_caching_supported(
    model: type_model_name, target: Literal["system", "message", "tool"]
) -> bool:
    return target in get_model_spec(model).prompt_caching


def is_prompt_caching_automatic(model: type_model_name) -> bool:
    """Strands places the cache points of Anthropic models itself: after the system
    prompt, after the tools and on the last user message, moving it forward as the
    agent loop adds tool results."""
    return get_model_spec(model).provider == "anthropic"


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


# The output limit for short answers, such as titles and summaries. It leaves
# room for models that always reason before answering.
SHORT_ANSWER_MAX_TOKENS = 2048


def call_converse_api(
    args: ConverseStreamRequestTypeDef, max_attempts: int = 1
) -> ConverseResponseTypeDef:
    """Call Converse once by default, for callers behind API Gateway's timeout.

    Args:
        args: The Converse request.
        max_attempts: The attempts, including retries of throttling and server
            errors, for callers without that timeout.
    """
    return get_bedrock_runtime_client(max_attempts=max_attempts).converse(**args)


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


# The model lookups run before chat answers and on every page load, behind API
# Gateway's 29-second timeout, so they are not retried, have a deadline, and a
# failed lookup is not repeated for a while.
_LOOKUP_DEADLINE_SECONDS = 10.0
_LOOKUP_RETRY_SECONDS = 60.0
_lookup_failed_at: dict[str, float] = {}


class ModelLookupUnavailable(Exception):
    """Bedrock could not list the models of the region."""


def _bedrock_client(region: str):
    return boto3.client(
        "bedrock",
        region_name=region,
        config=Config(
            connect_timeout=3,
            read_timeout=5,
            retries={"mode": "standard", "max_attempts": 1},
        ),
    )


@functools.cache
def _list_system_inference_profiles(region: str) -> dict[str, frozenset[str]]:
    """Return the system-defined inference profiles in the region.

    Returns:
        The ARNs of the models that each profile routes to, by profile ID.

    Raises:
        TimeoutError: If the pages take longer than the lookup deadline.
    """
    client = _bedrock_client(region)
    deadline = time.monotonic() + _LOOKUP_DEADLINE_SECONDS
    profiles: dict[str, frozenset[str]] = {}
    kwargs: dict[str, Any] = {"typeEquals": "SYSTEM_DEFINED", "maxResults": 1000}
    while True:
        response = client.list_inference_profiles(**kwargs)
        profiles.update(
            (
                profile["inferenceProfileId"],
                frozenset(model["modelArn"] for model in profile["models"]),
            )
            for profile in response["inferenceProfileSummaries"]
        )
        if "nextToken" not in response:
            return profiles
        if time.monotonic() > deadline:
            raise TimeoutError(f"Listing inference profiles in {region} took too long")
        kwargs["nextToken"] = response["nextToken"]


@functools.cache
def _list_on_demand_models(region: str) -> frozenset[str]:
    """Return the IDs of the foundation models with on-demand throughput in the region."""
    response = _bedrock_client(region).list_foundation_models(
        byInferenceType="ON_DEMAND"
    )
    return frozenset(model["modelId"] for model in response["modelSummaries"])


def _lookup(list_models: Callable[[str], _T], region: str) -> _T:
    """Run a cached model lookup, remembering a failure for a while.

    Raises:
        ModelLookupUnavailable: If the lookup failed now or recently.
    """
    failed_at = _lookup_failed_at.get(region)
    if failed_at is not None and time.monotonic() - failed_at < _LOOKUP_RETRY_SECONDS:
        raise ModelLookupUnavailable(f"A model lookup in {region} failed recently")
    try:
        return list_models(region)
    except (BotoCoreError, ClientError, TimeoutError) as e:
        _lookup_failed_at[region] = time.monotonic()
        raise ModelLookupUnavailable(f"Failed to list the models in {region}") from e


def _find_inference_profile(
    base_model_id: str,
    profiles: dict[str, frozenset[str]],
    enable_global: bool,
    enable_cross_region: bool,
) -> str | None:
    """Return the global profile, else a geographic profile, that routes to the model."""
    # Profiles route to foundation models in several regions, so their model ARNs
    # differ in the region but end with the same model ID.
    model_arn_suffix = f"foundation-model/{base_model_id}"
    profile_ids = {
        profile_id
        for profile_id, model_arns in profiles.items()
        if any(arn.endswith(model_arn_suffix) for arn in model_arns)
    }

    global_profile_id = f"global.{base_model_id}"
    if enable_global and global_profile_id in profile_ids:
        return global_profile_id

    if enable_cross_region:
        # Geographic profiles, such as "us." or "apac.".
        regional_profile_ids = sorted(profile_ids - {global_profile_id})
        if regional_profile_ids:
            return regional_profile_ids[0]
    return None


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

    try:
        profiles = _lookup(_list_system_inference_profiles, bedrock_region)
    except ModelLookupUnavailable:
        # Most current models are offered through a global profile, so try it rather
        # than failing every request while the lookup is unavailable.
        logger.warning(
            "Failed to list inference profiles in %s", bedrock_region, exc_info=True
        )
        return f"global.{base_model_id}" if enable_global else base_model_id

    profile_id = _find_inference_profile(
        base_model_id, profiles, enable_global, enable_cross_region
    )
    if profile_id:
        return profile_id

    logger.warning(
        "No inference profile for %s in %s. Using the base model ID, which only works "
        "if the model supports on-demand throughput in this region.",
        model,
        bedrock_region,
    )
    return base_model_id


def filter_available_models(
    models: list[str],
    enable_global: bool = ENABLE_BEDROCK_GLOBAL_INFERENCE,
    enable_cross_region: bool = ENABLE_BEDROCK_CROSS_REGION_INFERENCE,
    bedrock_region: str = BEDROCK_REGION,
) -> list[str]:
    """Keep the models that can be invoked from the region, through an inference
    profile or with on-demand throughput.

    A failed lookup keeps every model, so that a Bedrock outage does not hide them;
    a model that is not offered fails when it is used instead.
    """
    try:
        profiles = (
            _lookup(_list_system_inference_profiles, bedrock_region)
            if enable_global or enable_cross_region
            else {}
        )
        on_demand = _lookup(_list_on_demand_models, bedrock_region)
    except ModelLookupUnavailable:
        logger.warning(
            "Failed to list the models offered in %s", bedrock_region, exc_info=True
        )
        return list(models)

    def is_available(model: str) -> bool:
        try:
            base_model_id = get_model_spec(model).bedrock_id
        except ValueError:
            return False
        return base_model_id in on_demand or bool(
            profiles
            and _find_inference_profile(
                base_model_id, profiles, enable_global, enable_cross_region
            )
        )

    return [model for model in models if is_available(model)]
