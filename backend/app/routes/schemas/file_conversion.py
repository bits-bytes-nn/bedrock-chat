from app.routes.schemas.base import BaseSchema
from app.usecases.file_conversion import ConversionState
from pydantic import Field


class FileConversionOutput(BaseSchema):
    status: ConversionState
    reason: str = ""
    converted_filename: str = Field(
        ..., description="Name of the text file that the conversion produces."
    )


class AttachmentUploadOutput(BaseSchema):
    upload_id: str
    url: str


class AttachmentConversionOutput(BaseSchema):
    status: ConversionState
    reason: str = ""
    text: str | None = Field(None, description="The converted text when completed.")
