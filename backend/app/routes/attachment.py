from app.routes.schemas.file_conversion import (
    AttachmentConversionOutput,
    AttachmentUploadOutput,
)
from app.usecases.file_conversion import (
    DOCUMENT_BUCKET,
    ConversionStatus,
    chat_upload_key,
    get_conversion,
    read_converted_text,
    start_conversion,
)
from app.user import User
from app.utils import generate_presigned_url
from fastapi import APIRouter, Request
from ulid import ULID

router = APIRouter(tags=["attachment"])


def _output(status: ConversionStatus, key: str) -> AttachmentConversionOutput:
    return AttachmentConversionOutput(
        status=status.status,
        reason=status.reason,
        text=read_converted_text(key) if status.status == "COMPLETED" else None,
    )


@router.get("/attachments/presigned-url", response_model=AttachmentUploadOutput)
def get_attachment_upload_url(request: Request, filename: str, contentType: str):
    """Issue an upload URL for a chat attachment that must be converted to text,
    such as a presentation or a recording."""
    current_user: User = request.state.current_user
    upload_id = str(ULID())
    url = generate_presigned_url(
        DOCUMENT_BUCKET,
        chat_upload_key(current_user.id, upload_id, filename),
        content_type=contentType,
        expiration=3600,
        client_method="put_object",
    )
    return AttachmentUploadOutput(upload_id=upload_id, url=url)


@router.post(
    "/attachments/{upload_id}/conversion", response_model=AttachmentConversionOutput
)
def post_attachment_conversion(request: Request, upload_id: str, filename: str):
    """Start converting an uploaded attachment into text."""
    current_user: User = request.state.current_user
    key = chat_upload_key(current_user.id, upload_id, filename)
    return _output(start_conversion(key), key)


@router.get(
    "/attachments/{upload_id}/conversion", response_model=AttachmentConversionOutput
)
def get_attachment_conversion(request: Request, upload_id: str, filename: str):
    """Return the conversion status, with the text once it is completed."""
    current_user: User = request.state.current_user
    key = chat_upload_key(current_user.id, upload_id, filename)
    return _output(get_conversion(key), key)
