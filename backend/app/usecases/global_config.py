import json
import logging
import os

from app.model_registry import MODELS
from app.routes.schemas.conversation import type_model_name

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s - %(message)s")
logger = logging.getLogger(__name__)

GLOBAL_AVAILABLE_MODELS = os.environ.get("GLOBAL_AVAILABLE_MODELS")
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL")
TITLE_MODEL = os.environ.get("TITLE_MODEL")
LOGO_PATH = os.environ.get("LOGO_PATH", "")


def get_global_available_models() -> list[str]:
    """
    Get the list of globally available models from environment variable.
    Returns empty list if not configured or if an empty array is provided,
    which means all models are available.
    """
    if GLOBAL_AVAILABLE_MODELS:
        try:
            models = json.loads(GLOBAL_AVAILABLE_MODELS)
            # Ensure the result is a list
            if isinstance(models, list):
                logger.info(f"Global available models (JSON): {models}")
                # Filter out empty strings and None values
                filtered_models = [
                    model for model in models if model and isinstance(model, str)
                ]
                return filtered_models
            else:
                logger.error(
                    f"GLOBAL_AVAILABLE_MODELS must be a JSON array, got {type(models)}"
                )
                return []
        except json.JSONDecodeError:
            logger.error("Failed to parse GLOBAL_AVAILABLE_MODELS as JSON")
            return []

    logger.info("No global available models configured - all models are available")
    return []


def _first_available_model(*candidates: str | None) -> str | None:
    for candidate in candidates:
        model = (candidate or "").strip()
        if not model:
            continue
        if model in MODELS:
            return model
        logger.warning("Ignoring configured model %s: it is retired or unknown", model)
    return None


def get_default_model() -> type_model_name:
    """Return the configured default model, falling back to claude-v5.5-sonnet."""
    return _first_available_model(DEFAULT_MODEL) or "claude-v5.5-sonnet"  # type: ignore[return-value]


def get_title_model() -> type_model_name:
    """Return the model for title generation.

    Falls back to: TITLE_MODEL -> DEFAULT_MODEL -> claude-v5.5-haiku
    """
    return _first_available_model(TITLE_MODEL, DEFAULT_MODEL) or "claude-v5.5-haiku"  # type: ignore[return-value]


def get_logo_path() -> str:
    """Return the configured drawer logo path."""
    return LOGO_PATH
