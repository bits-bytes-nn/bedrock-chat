from fastapi import APIRouter

from app.usecases.global_config import (
    get_logo_path,
    get_selectable_models,
    get_default_model,
)

router = APIRouter(tags=["config"])


@router.get("/config/global")
def get_global_config():
    """Get global configuration including the models that users can choose."""
    global_models = get_selectable_models()
    default_model = get_default_model()
    logo_path = get_logo_path()
    return {
        "globalAvailableModels": global_models,
        "defaultModel": default_model,
        "logoPath": logo_path,
    }
