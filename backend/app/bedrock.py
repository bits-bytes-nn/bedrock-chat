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
    TypeGuard,
)

import boto3
from app.config import DEFAULT_GENERATION_CONFIG
from app.model_registry import get_model_spec
from app.repositories.models.custom_bot import GenerationParamsModel
from app.repositories.models.custom_bot_guardrails import BedrockGuardrailsModel
from app.routes.schemas.conversation import type_model_name
from app.utils import get_bedrock_runtime_client
from app.vector_search import SearchResult

if TYPE_CHECKING:
    from app.repositories.models.conversation import ContentModel, SimpleMessageModel
    from mypy_boto3_bedrock_runtime.literals import ConversationRoleType
    from mypy_boto3_bedrock_runtime.type_defs import (
        ContentBlockTypeDef,
        ConverseResponseTypeDef,
        ConverseStreamRequestTypeDef,
        GuardrailConverseContentBlockTypeDef,
        MessageTypeDef,
        SystemContentBlockTypeDef,
    )


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "us-east-1")
ENABLE_BEDROCK_GLOBAL_INFERENCE = (
    os.environ.get("ENABLE_BEDROCK_GLOBAL_INFERENCE", "false") == "true"
)
ENABLE_BEDROCK_CROSS_REGION_INFERENCE = (
    os.environ.get("ENABLE_BEDROCK_CROSS_REGION_INFERENCE", "false") == "true"
)

# Base model IDs mapping


def _is_conversation_role(role: str) -> TypeGuard[ConversationRoleType]:
    return role in ["user", "assistant"]


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


def is_multiple_system_prompt_content_supported(model: type_model_name) -> bool:
    return get_model_spec(model).supports_multiple_system_prompts


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


def _to_guardrails_grounding_source(
    search_results: list[SearchResult],
) -> GuardrailConverseContentBlockTypeDef | None:
    """Convert search results to Guardrails Grounding source format."""
    return (
        {
            "text": {
                "text": "\n\n".join(x["content"] for x in search_results),
                "qualifiers": ["grounding_source"],
            }
        }
        if len(search_results) > 0
        else None
    )


def simple_message_models_to_bedrock_messages(
    simple_messages: list[SimpleMessageModel],
    model: type_model_name,
    guardrail: BedrockGuardrailsModel | None = None,
    search_results: list[SearchResult] | None = None,
    prompt_caching_enabled: bool = True,
) -> list[MessageTypeDef]:
    grounding_source = None
    if search_results and guardrail and guardrail.is_guardrail_enabled:
        grounding_source = _to_guardrails_grounding_source(search_results)

    def process_content(c: ContentModel, role: str) -> list[ContentBlockTypeDef]:
        # Drop unsigned reasoning blocks for DeepSeek R1 and GPT-OSS models
        if (
            not is_unsigned_reasoning_content_supported(model)
            and c.content_type == "reasoning"
            and not getattr(c, "signature", None)
        ):
            return []

        if c.content_type == "text":
            if (
                role == "user"
                and guardrail
                and guardrail.grounding_threshold > 0
                and grounding_source
            ):
                return [
                    {"guardContent": grounding_source},
                    {
                        "guardContent": {
                            "text": {"text": c.body, "qualifiers": ["query"]}
                        }
                    },
                ]

        return c.to_contents_for_converse()

    messages: list[MessageTypeDef] = [
        {
            "role": message.role,
            "content": [
                block
                for c in message.content
                for block in process_content(c, message.role)
            ],
        }
        for message in simple_messages
        if _is_conversation_role(message.role)
    ]

    if prompt_caching_enabled and is_prompt_caching_supported(model, target="message"):
        for order, message in enumerate(
            filter(lambda m: m["role"] == "user", reversed(messages))
        ):
            if order >= 2:
                break

            message["content"] = [
                *(message["content"]),
                {
                    "cachePoint": {"type": "default"},
                },
            ]

    return messages


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
    if spec.supports_stop_sequences and stop_sequences and any(stop_sequences):
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


def compose_args_for_converse_api(
    messages: list[SimpleMessageModel],
    model: type_model_name,
    instructions: list[str] = [],
    generation_params: GenerationParamsModel | None = None,
    guardrail: BedrockGuardrailsModel | None = None,
    search_results: list[SearchResult] | None = None,
    stream: bool = True,
    enable_reasoning: bool = False,
    prompt_caching_enabled: bool = False,
) -> ConverseStreamRequestTypeDef:
    arg_messages = simple_message_models_to_bedrock_messages(
        simple_messages=messages,
        model=model,
        guardrail=guardrail,
        search_results=search_results,
        prompt_caching_enabled=prompt_caching_enabled,
    )
    # Prepare model-specific parameters
    converse_config = generation_params_to_converse_configuration(
        model=model,
        generation_params=generation_params,
        guardrail=guardrail,
        stream=stream,
        enable_reasoning=enable_reasoning,
    )

    system_prompts: list[SystemContentBlockTypeDef]

    if is_multiple_system_prompt_content_supported(model):
        system_prompts = [
            {
                "text": instruction,
            }
            for instruction in instructions
            if len(instruction) > 0
        ]

    else:
        system_prompts = (
            [
                {
                    "text": "\n\n".join(instructions),
                }
            ]
            if instructions and any(instructions)
            else []
        )

    if (
        prompt_caching_enabled
        and is_prompt_caching_supported(model, "system")
        and len(system_prompts) > 0
    ):
        system_prompts.append(
            {
                "cachePoint": {
                    "type": "default",
                },
            }
        )

    # Construct the base arguments
    args: ConverseStreamRequestTypeDef = {
        "inferenceConfig": {},
        "modelId": get_model_id(model),
        "messages": arg_messages,
        "system": system_prompts,
    }

    inference_config = converse_config["inferenceConfig"]
    if "temperature" in inference_config:
        args["inferenceConfig"]["temperature"] = inference_config["temperature"]

    if "topP" in inference_config:
        args["inferenceConfig"]["topP"] = inference_config["topP"]

    if "maxTokens" in inference_config:
        args["inferenceConfig"]["maxTokens"] = inference_config["maxTokens"]

    if "stopSequences" in inference_config:
        args["inferenceConfig"]["stopSequences"] = inference_config["stopSequences"]

    if "additionalModelRequestFields" in converse_config:
        args["additionalModelRequestFields"] = converse_config[
            "additionalModelRequestFields"
        ]

    if "guardrailConfig" in converse_config:
        args["guardrailConfig"] = converse_config["guardrailConfig"]

    return args


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
    if price is None:
        logger.warning("No price is defined for model %s. Reporting 0.", model)
        return 0.0

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
    client = boto3.client("bedrock", region_name=region)
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

    profile_ids = _list_system_inference_profile_ids(bedrock_region)
    global_profile_id = f"global.{base_model_id}"
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

    logger.info(
        "No inference profile for %s in %s. Using the base model ID.",
        model,
        bedrock_region,
    )
    return base_model_id
