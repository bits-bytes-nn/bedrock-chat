from typing import Literal

from app.routes.schemas.base import BaseSchema
from pydantic import Field


class FileConversionOutput(BaseSchema):
    status: Literal["IN_PROGRESS", "COMPLETED", "FAILED"]
    reason: str = ""
    converted_filename: str = Field(
        ..., description="Name of the text file that the conversion produces."
    )


class AttachmentUploadOutput(BaseSchema):
    upload_id: str
    url: str


class AttachmentConversionOutput(BaseSchema):
    status: Literal["IN_PROGRESS", "COMPLETED", "FAILED"]
    reason: str = ""
    text: str | None = Field(None, description="The converted text when completed.")
