from typing import Literal

from app.routes.schemas.base import BaseSchema
from pydantic import Field, model_validator


class PublishedApiQuota(BaseSchema):
    limit: int | None
    offset: int | None
    period: Literal["DAY", "WEEK", "MONTH"] | None

    # Validate after parsing so that camelCase and snake_case input are both checked.
    @model_validator(mode="after")
    def validate_quota(self):
        if (self.limit is None) != (self.period is None):
            raise ValueError("limit and period must both be None or both have values")
        if self.limit is not None and self.limit <= 0:
            raise ValueError("limit must be a positive integer")
        return self


class PublishedApiThrottle(BaseSchema):
    rate_limit: float | None
    burst_limit: int | None

    @model_validator(mode="after")
    def validate_throttle(self):
        rate_limit, burst_limit = self.rate_limit, self.burst_limit
        if (rate_limit is None) != (burst_limit is None):
            raise ValueError(
                "rate_limit and burst_limit must both be None or both have values"
            )
        if rate_limit is not None and rate_limit <= 0:
            raise ValueError("rate_limit must be a positive number")
        if burst_limit is not None and burst_limit <= 0:
            raise ValueError("burst_limit must be a positive integer")
        return self


class BotPublishInput(BaseSchema):
    stage: str | None  # "dev" | "stg" | "prd" | etc.
    quota: PublishedApiQuota
    throttle: PublishedApiThrottle
    allowed_origins: list[str]

    @model_validator(mode="after")
    def validate_allowed_origins(self):
        for origin in self.allowed_origins:
            if not (origin.startswith(("http://", "https://")) or origin == "*"):
                raise ValueError(
                    f"Invalid origin: {origin}. Origin must start with 'http://' or 'https://' or be '*'"
                )
        return self


class BotPublishOutput(BaseSchema):
    stage: str = Field(
        ...,
        description="The stage of the API Gateway (e.g. dev, stg, prd). Default value is `api`.",
    )
    quota: PublishedApiQuota
    throttle: PublishedApiThrottle
    allowed_origins: list[str]
    cfn_status: str = Field(
        ..., description="The status of the cloudformation deployment."
    )
    codebuild_id: str = Field(
        ..., description="The id of the codebuild for cfn deployment."
    )
    codebuild_status: str = Field(..., description="The status of the codebuild.")
    endpoint: str | None = Field(..., description="The endpoint of the API Gateway.")
    api_key_ids: list[str]


class ApiKeyInput(BaseSchema):
    description: str


class ApiKeyOutput(BaseSchema):
    id: str
    description: str
    value: str
    enabled: bool
    created_date: int
