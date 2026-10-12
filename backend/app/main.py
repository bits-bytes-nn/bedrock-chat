import logging
import os
import traceback
from typing import Callable

from app.dependencies import get_current_user
from app.repositories.common import (
    RecordAccessNotAllowedError,
    RecordNotFoundError,
    ResourceConflictError,
)
from app.routes.admin import router as admin_router
from app.routes.attachment import router as attachment_router
from app.routes.api_publication import router as api_publication_router
from app.routes.bot import router as bot_router
from app.routes.bot_store import router as bot_store_router
from app.routes.conversation import router as conversation_router
from app.routes.global_config import router as global_config_router
from app.routes.published_api import router as published_api_router
from app.routes.user import router as user_router
from app.user import User
from app.utils import is_running_on_lambda
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import ValidationError
from starlette.responses import Response
from starlette.types import ASGIApp

CORS_ALLOW_ORIGINS = os.environ.get("CORS_ALLOW_ORIGINS", "*")
PUBLISHED_API_ID = os.environ.get("PUBLISHED_API_ID", None)

is_published_api = PUBLISHED_API_ID is not None

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s - %(message)s")
logger = logging.getLogger(__name__)

if not is_published_api:
    openapi_tags = [
        {"name": "conversation", "description": "Conversation API"},
        {"name": "bot", "description": "Bot API"},
        {"name": "api_publication", "description": "API Publication API"},
        {"name": "admin", "description": "Admin API"},
        {"name": "user", "description": "User API (cognito)"},
        {"name": "bot_store", "description": "Bot Store API"},
        {"name": "config", "description": "Global Configuration API"},
    ]
    title = "Bedrock Chat"
else:
    openapi_tags = [{"name": "published_api", "description": "Published API"}]
    title = "Bedrock Chat Published API"


app = FastAPI(
    openapi_tags=openapi_tags,
    title=title,
)


if not is_published_api:
    app.include_router(conversation_router)
    app.include_router(attachment_router)
    app.include_router(bot_router)
    app.include_router(api_publication_router)
    app.include_router(admin_router)
    app.include_router(user_router)
    app.include_router(bot_store_router)
    app.include_router(global_config_router)
else:
    app.include_router(published_api_router)


app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def error_handler_factory(status_code: int) -> Callable[[Request, Exception], Response]:
    def error_handler(_: Request, exc: Exception) -> JSONResponse:
        logger.error(exc)
        logger.error("".join(traceback.format_tb(exc.__traceback__)))
        # Unexpected errors may contain resource names and account details.
        message = str(exc) if status_code < 500 else "Internal server error"
        return JSONResponse({"errors": [message]}, status_code=status_code)

    return error_handler  # type: ignore


app.add_exception_handler(RecordNotFoundError, error_handler_factory(404))
app.add_exception_handler(FileNotFoundError, error_handler_factory(404))
app.add_exception_handler(RecordAccessNotAllowedError, error_handler_factory(403))
app.add_exception_handler(ValueError, error_handler_factory(400))
app.add_exception_handler(PermissionError, error_handler_factory(403))
app.add_exception_handler(ValidationError, error_handler_factory(422))
app.add_exception_handler(ResourceConflictError, error_handler_factory(409))
app.add_exception_handler(Exception, error_handler_factory(500))


def _user_from_authorization(authorization: str) -> User:
    scheme, _, credentials = authorization.partition(" ")
    if scheme.lower() != "bearer" or not credentials:
        raise HTTPException(status_code=403, detail="Could not validate credentials")
    return get_current_user(
        HTTPAuthorizationCredentials(scheme="Bearer", credentials=credentials)
    )


@app.middleware("http")
async def add_current_user_to_request(request: Request, call_next: ASGIApp):
    authorization = request.headers.get("Authorization")
    try:
        if is_published_api and is_running_on_lambda():
            assert PUBLISHED_API_ID is not None, "PUBLISHED_API_ID is not set."
            request.state.current_user = User.from_published_api_id(PUBLISHED_API_ID)
        elif authorization:
            request.state.current_user = _user_from_authorization(authorization)
        elif not is_running_on_lambda():
            request.state.current_user = User(
                id="test_user", name="test_user", email="user@example.com", groups=[]
            )
    except HTTPException as e:
        # Exception handlers do not run for errors raised in middleware.
        return JSONResponse({"errors": [e.detail]}, status_code=e.status_code)

    return await call_next(request)  # type: ignore


@app.middleware("http")
async def add_log_requests(request: Request, call_next: ASGIApp):
    # Headers and bodies are not logged because they contain tokens and user content.
    logger.info("Request: %s %s", request.method, request.url.path)

    response = await call_next(request)  # type: ignore

    return response
