"""Single source of truth for the models offered by the application.

Each entry describes how to call the model through the Bedrock Converse API. Parameter
support was verified with Converse calls. Prices come from the AWS Price List API or
the Bedrock model cards and are per 1,000 tokens for global cross-Region inference.
"""

from dataclasses import dataclass, field, replace
from typing import Literal

from app.config import (
    DEFAULT_GENERATION_CONFIG,
    DEFAULT_MISTRAL_GENERATION_CONFIG,
    DEFAULT_NOVA_GENERATION_CONFIG,
    GenerationParams,
)

Provider = Literal["anthropic", "amazon", "openai", "mistral"]
CachingTarget = Literal["system", "message", "tool"]


@dataclass(frozen=True)
class ModelPrice:
    """USD per 1,000 tokens."""

    input: float
    output: float
    cache_read_input: float | None = None
    cache_write_input: float | None = None


@dataclass(frozen=True)
class ModelSpec:
    bedrock_id: str
    provider: Provider
    price: ModelPrice
    defaults: GenerationParams = field(
        default_factory=lambda: DEFAULT_GENERATION_CONFIG
    )
    # Used when no generation parameters are given, for example outside of a bot.
    default_max_tokens: int = 4096
    # "budget" and "adaptive" are Claude extended thinking modes that the user can
    # toggle. "always" models return reasoning on every request.
    reasoning: Literal["none", "budget", "adaptive", "always"] = "none"
    supports_temperature: bool = True
    supports_top_p: bool = True
    # Claude 4.1+ models reject requests that set both temperature and top_p.
    exclusive_temperature_top_p: bool = False
    # Where top_k goes in additionalModelRequestFields, if supported.
    top_k_field: Literal["claude", "nova"] | None = None
    supports_stop_sequences: bool = True
    supports_tool_use: bool = True
    # Converse document blocks. Attachments are sent as text to models without them.
    supports_documents: bool = True
    prompt_caching: frozenset[CachingTarget] = frozenset()
    # Reasoning blocks without a signature cannot be sent back to these models.
    accepts_unsigned_reasoning: bool = True


_ALL_CACHING: frozenset[CachingTarget] = frozenset({"system", "message", "tool"})

# How long Claude cache points live. Writes cost more for an hour (2x the input
# price) than for 5 minutes (1.25x), and reads 0.1x either way, so an hour pays off
# when enough follow-up messages come 5-60 minutes later
# (https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html).
CLAUDE_CACHE_TTL: Literal["5m", "1h"] = "1h"
_CACHE_WRITE_PRICE_FACTOR = {"5m": 1.25, "1h": 2.0}


def _claude(
    bedrock_id: str,
    price: ModelPrice,
    reasoning: Literal["budget", "adaptive"],
    *,
    modern: bool = False,
) -> ModelSpec:
    """Claude 4.5 and later. Modern models (Opus 4.7 and later) reject sampling
    parameters.

    Cache points live for CLAUDE_CACHE_TTL, whose write price follows from the
    input price, so the price passes the input, output and read rates only.
    """
    assert price.cache_write_input is None, "derived from CLAUDE_CACHE_TTL"
    return ModelSpec(
        bedrock_id=bedrock_id,
        provider="anthropic",
        price=replace(
            price,
            cache_write_input=price.input * _CACHE_WRITE_PRICE_FACTOR[CLAUDE_CACHE_TTL],
        ),
        default_max_tokens=16384,
        reasoning=reasoning,
        supports_temperature=not modern,
        supports_top_p=not modern,
        exclusive_temperature_top_p=not modern,
        top_k_field=None if modern else "claude",
        prompt_caching=_ALL_CACHING,
    )


def _gpt(bedrock_id: str, price: ModelPrice) -> ModelSpec:
    """OpenAI GPT-5.5 and later. Converse rejects temperature, topP, stopSequences,
    cache points and document blocks for these models."""
    return ModelSpec(
        bedrock_id=bedrock_id,
        provider="openai",
        price=price,
        default_max_tokens=16384,
        reasoning="always",
        supports_temperature=False,
        supports_top_p=False,
        supports_stop_sequences=False,
        supports_documents=False,
        accepts_unsigned_reasoning=False,
    )


def _nova(bedrock_id: str, price: ModelPrice) -> ModelSpec:
    return ModelSpec(
        bedrock_id=bedrock_id,
        provider="amazon",
        price=price,
        defaults=DEFAULT_NOVA_GENERATION_CONFIG,
        top_k_field="nova",
        prompt_caching=frozenset({"system", "message"}),
    )


def _mistral(bedrock_id: str, price: ModelPrice) -> ModelSpec:
    return ModelSpec(
        bedrock_id=bedrock_id,
        provider="mistral",
        price=price,
        defaults=DEFAULT_MISTRAL_GENERATION_CONFIG,
    )


def _gpt_oss(bedrock_id: str, price: ModelPrice) -> ModelSpec:
    return ModelSpec(
        bedrock_id=bedrock_id,
        provider="openai",
        price=price,
        default_max_tokens=8192,
        reasoning="always",
        supports_stop_sequences=False,
        accepts_unsigned_reasoning=False,
    )


_OPUS_4_5_PRICE = ModelPrice(0.005, 0.025, 0.0005)
_SONNET_4_PRICE = ModelPrice(0.003, 0.015, 0.0003)

MODELS: dict[str, ModelSpec] = {
    "claude-v4.5-opus": _claude(
        "anthropic.claude-opus-4-5-20251101-v1:0", _OPUS_4_5_PRICE, "budget"
    ),
    "claude-v4.6-opus": _claude(
        "anthropic.claude-opus-4-6-v1",
        _OPUS_4_5_PRICE,
        "adaptive",
    ),
    "claude-v4.7-opus": _claude(
        "anthropic.claude-opus-4-7", _OPUS_4_5_PRICE, "adaptive", modern=True
    ),
    "claude-v4.8-opus": _claude(
        "anthropic.claude-opus-4-8", _OPUS_4_5_PRICE, "adaptive", modern=True
    ),
    "claude-v5-opus": _claude(
        "anthropic.claude-opus-5", _OPUS_4_5_PRICE, "adaptive", modern=True
    ),
    "claude-v5.5-opus": _claude(
        "anthropic.claude-opus-5-5",
        ModelPrice(0.004, 0.02, 0.0002),
        "adaptive",
        modern=True,
    ),
    "claude-v4.5-sonnet": _claude(
        "anthropic.claude-sonnet-4-5-20250929-v1:0", _SONNET_4_PRICE, "budget"
    ),
    "claude-v4.6-sonnet": _claude(
        "anthropic.claude-sonnet-4-6",
        _SONNET_4_PRICE,
        "adaptive",
    ),
    "claude-v5-sonnet": _claude(
        "anthropic.claude-sonnet-5",
        ModelPrice(0.002, 0.01, 0.0002),
        "adaptive",
        modern=True,
    ),
    "claude-v5.5-sonnet": _claude(
        "anthropic.claude-sonnet-5-5",
        ModelPrice(0.002, 0.01, 0.0001),
        "adaptive",
        modern=True,
    ),
    "claude-v4.5-haiku": _claude(
        "anthropic.claude-haiku-4-5-20251001-v1:0",
        ModelPrice(0.001, 0.005, 0.0001),
        "budget",
    ),
    "claude-v5.5-haiku": _claude(
        "anthropic.claude-haiku-5-5",
        ModelPrice(0.0001, 0.0005, 0.00001),
        "adaptive",
        modern=True,
    ),
    # GPT-5.5 has no global cross-Region price; this is the In-Region price.
    "gpt-5.5": _gpt("openai.gpt-5.5", ModelPrice(0.0055, 0.033, 0.00055)),
    "gpt-5.6-luna": _gpt(
        "openai.gpt-5.6-luna", ModelPrice(0.0002, 0.0012, 0.00002, 0.00025)
    ),
    "gpt-5.6-sol": _gpt("openai.gpt-5.6-sol", ModelPrice(0.004, 0.02, 0.0004, 0.005)),
    "gpt-5.6-terra": _gpt(
        "openai.gpt-5.6-terra", ModelPrice(0.002, 0.012, 0.0002, 0.0025)
    ),
    "gpt-6-astra": _gpt("openai.gpt-6-astra", ModelPrice(0.01, 0.05, 0.001, 0.0125)),
    "gpt-6-luna": _gpt(
        "openai.gpt-6-luna", ModelPrice(0.0001, 0.0005, 0.00001, 0.000125)
    ),
    "gpt-6-sol": _gpt("openai.gpt-6-sol", ModelPrice(0.002, 0.01, 0.0002, 0.0025)),
    "gpt-6.1-sol": _gpt("openai.gpt-6.1-sol", ModelPrice(0.002, 0.01, 0.0001, 0.0025)),
    "gpt-6.2-astra": _gpt(
        "openai.gpt-6.2-astra", ModelPrice(0.008, 0.04, 0.0004, 0.01)
    ),
    "gpt-6.2-sol": _gpt("openai.gpt-6.2-sol", ModelPrice(0.002, 0.01, 0.0001, 0.0025)),
    "gpt-6.1-terra": _gpt(
        "openai.gpt-6.1-terra", ModelPrice(0.001, 0.005, 0.00005, 0.00125)
    ),
    "gpt-oss-20b": _gpt_oss("openai.gpt-oss-20b-1:0", ModelPrice(0.00015, 0.0003)),
    "gpt-oss-120b": _gpt_oss("openai.gpt-oss-120b-1:0", ModelPrice(0.0003, 0.0006)),
    # Amazon Nova does not charge for cache writes (AWS Price List API).
    "amazon-nova-pro": _nova(
        "amazon.nova-pro-v1:0", ModelPrice(0.0008, 0.0032, 0.0002, 0.0)
    ),
    "amazon-nova-lite": _nova(
        "amazon.nova-lite-v1:0", ModelPrice(0.00006, 0.00024, 0.000015, 0.0)
    ),
    "amazon-nova-micro": _nova(
        "amazon.nova-micro-v1:0",
        ModelPrice(0.000035, 0.00014, 0.00000875, 0.0),
    ),
    "amazon-nova-2-lite": _nova(
        "amazon.nova-2-lite-v1:0", ModelPrice(0.0003, 0.0025, 0.000075, 0.0)
    ),
    "mistral-large": _mistral(
        "mistral.mistral-large-2402-v1:0", ModelPrice(0.004, 0.012)
    ),
    "mistral-large-2": _mistral(
        "mistral.mistral-large-2407-v1:0", ModelPrice(0.002, 0.006)
    ),
}

# Models that Bedrock no longer offers. Their names stay valid so that existing
# conversations and bots can be read, but they cannot be used for new messages.
RETIRED_MODELS: frozenset[str] = frozenset(
    {
        "claude-v3-haiku",
        "claude-v3-opus",
        "claude-v3.5-haiku",
        "claude-v3.5-sonnet",
        "claude-v3.5-sonnet-v2",
        "claude-v3.7-sonnet",
        "claude-v4-opus",
        "claude-v4-sonnet",
        "claude-v4.1-opus",
        "deepseek-r1",
        "llama3-3-70b-instruct",
        "mistral-7b-instruct",
        "mixtral-8x7b-instruct",
        "llama3-2-1b-instruct",
        "llama3-2-3b-instruct",
        "llama3-2-11b-instruct",
        "llama3-2-90b-instruct",
    }
)


def get_model_spec(model: str) -> ModelSpec:
    """Return the specification of an available model.

    Raises:
        ValueError: If the model is retired or unknown.
    """
    if model in RETIRED_MODELS:
        raise ValueError(
            f"Model {model} has been retired from Amazon Bedrock. Choose another model."
        )
    try:
        return MODELS[model]
    except KeyError:
        raise ValueError(f"Unsupported model: {model}") from None
