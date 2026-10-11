"""Types passed to the streaming callbacks of chat()."""

from typing import Literal, TypedDict

from app.repositories.models.conversation import MessageModel, RelatedDocumentModel
from pydantic import JsonValue
from strands.types.event_loop import StopReason


class OnStopInput(TypedDict):
    message: MessageModel
    stop_reason: StopReason
    input_token_count: int
    output_token_count: int
    cache_read_input_count: int
    cache_write_input_count: int
    price: float


class OnThinking(TypedDict):
    tool_use_id: str
    name: str
    input: dict[str, JsonValue]


class ToolRunResult(TypedDict):
    tool_use_id: str
    status: Literal["success", "error"]
    related_documents: list[RelatedDocumentModel]
