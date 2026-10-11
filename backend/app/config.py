from typing_extensions import NotRequired, TypedDict


class GenerationParams(TypedDict):
    max_tokens: int
    top_k: NotRequired[int]
    top_p: float
    temperature: float
    stop_sequences: list[str]
    reasoning_params: NotRequired[dict[str, int]]


# Configure generation parameter for Claude chat response.
# Adjust the values according to your application.
# See: https://docs.anthropic.com/claude/reference/complete_post
DEFAULT_GENERATION_CONFIG: GenerationParams = {
    # Minimum (Haiku) is 4096
    # Ref: https://docs.anthropic.com/en/docs/about-claude/models/all-models#model-comparison
    "max_tokens": 4096,
    "top_k": 250,
    "top_p": 0.999,
    "temperature": 1.0,
    "stop_sequences": [],
    # Budget tokens must NOT exceeds max_tokens
    "reasoning_params": {"budget_tokens": 1024},
}

# Ref: https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-mistral.html#model-parameters-mistral-request-response
DEFAULT_MISTRAL_GENERATION_CONFIG: GenerationParams = {
    "max_tokens": 4096,
    "top_p": 0.9,
    "temperature": 0.5,
    "stop_sequences": ["[INST]", "[/INST]"],
}

# Ref: https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-deepseek.html
DEFAULT_DEEP_SEEK_GENERATION_CONFIG: GenerationParams = {
    "max_tokens": 4096,
    "top_p": 0.9,
    "temperature": 1.0,
    "stop_sequences": [],
}

# Ref: https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-meta.html
DEFAULT_LLAMA_GENERATION_CONFIG: GenerationParams = {
    "max_tokens": 2048,
    "top_p": 0.9,
    "temperature": 0.7,
    "stop_sequences": [],
}

# Ref: https://docs.aws.amazon.com/nova/latest/userguide/getting-started-converse.html
# top_k is sent only when a bot sets it.
DEFAULT_NOVA_GENERATION_CONFIG: GenerationParams = {
    "max_tokens": 4096,
    "top_p": 0.999,
    "temperature": 1.0,
    "stop_sequences": [],
}
