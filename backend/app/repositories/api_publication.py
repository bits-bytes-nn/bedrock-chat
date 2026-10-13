import logging

import boto3
from app.repositories.common import RecordNotFoundError
from botocore.exceptions import ClientError
from app.repositories.models.api_publication import (
    ApiKeyModel,
    ApiUsagePlanModel,
    ApiUsagePlanQuotaModel,
    ApiUsagePlanThrottleModel,
    PublishedApiStackModel,
)
from ulid import ULID

logger = logging.getLogger(__name__)


def find_usage_plan_by_id(usage_plan_id: str) -> ApiUsagePlanModel:
    client = boto3.client("apigateway")
    try:
        plan_response = client.get_usage_plan(usagePlanId=usage_plan_id)
    except client.exceptions.NotFoundException:
        raise RecordNotFoundError("The usage plan does not exist.")

    key_ids = [
        key["id"]
        for page in client.get_paginator("get_usage_plan_keys").paginate(
            usagePlanId=usage_plan_id
        )
        for key in page["items"]
    ]

    return ApiUsagePlanModel(
        id=plan_response["id"],
        name=plan_response["name"],
        quota=ApiUsagePlanQuotaModel(
            limit=plan_response.get("quota", {}).get("limit"),
            offset=plan_response.get("quota", {}).get("offset"),
            period=plan_response.get("quota", {}).get("period"),
        ),
        throttle=ApiUsagePlanThrottleModel(
            rate_limit=plan_response.get("throttle", {}).get("rateLimit"),
            burst_limit=plan_response.get("throttle", {}).get("burstLimit"),
        ),
        key_ids=key_ids,
    )


def find_api_key_by_id(key_id: str, include_value: bool = False) -> ApiKeyModel:
    client = boto3.client("apigateway")
    response = client.get_api_key(apiKey=key_id, includeValue=include_value)
    return ApiKeyModel(
        id=response["id"],
        description=response.get("description", ""),
        value=response["value"] if include_value else "",
        enabled=response["enabled"],
        created_date=response["createdDate"].timestamp() * 1000,
    )


def create_api_key(usage_plan_id: str, description: str) -> ApiKeyModel:
    client = boto3.client("apigateway")
    response = client.create_api_key(
        name=str(ULID()),
        description=description,
        enabled=True,
    )
    api_key_id = response["id"]
    client.create_usage_plan_key(
        usagePlanId=usage_plan_id, keyId=api_key_id, keyType="API_KEY"
    )

    return ApiKeyModel(
        id=api_key_id,
        value="",
        description=description,
        enabled=True,
        created_date=response["createdDate"].timestamp() * 1000,
    )


def delete_api_key(api_key_id: str):
    client = boto3.client("apigateway")
    response = client.delete_api_key(apiKey=api_key_id)
    return response


def find_stack_by_bot_id(bot_id: str) -> PublishedApiStackModel:
    client = boto3.client("cloudformation")
    # DO NOT change the stack naming rule
    stack_name = f"ApiPublishmentStack{bot_id}"

    try:
        response = client.describe_stacks(StackName=stack_name)
    except client.exceptions.ClientError as e:
        # Other errors, such as throttling, must not look like a missing stack.
        if "does not exist" in e.response["Error"].get("Message", ""):
            raise RecordNotFoundError() from e
        raise

    stack = response["Stacks"][0]

    if stack["StackStatus"] != "CREATE_COMPLETE":
        return PublishedApiStackModel(
            stack_id=stack["StackId"],
            stack_name=stack["StackName"],
            stack_status=stack["StackStatus"],
            api_id=None,
            api_name=None,
            api_usage_plan_id=None,
            api_allowed_origins=None,
            api_stage=None,
            create_time=int(stack["CreationTime"].timestamp() * 1000),
        )

    return PublishedApiStackModel(
        stack_id=stack["StackId"],
        stack_name=stack["StackName"],
        stack_status=stack["StackStatus"],
        api_id=[
            output["OutputValue"]
            for output in stack["Outputs"]
            if output["OutputKey"] == "ApiId"
        ][0],
        api_name=[
            output["OutputValue"]
            for output in stack["Outputs"]
            if output["OutputKey"] == "ApiName"
        ][0],
        api_usage_plan_id=[
            output["OutputValue"]
            for output in stack["Outputs"]
            if output["OutputKey"] == "ApiUsagePlanId"
        ][0],
        api_allowed_origins=[
            output["OutputValue"]
            for output in stack["Outputs"]
            if output["OutputKey"] == "AllowedOrigins"
        ][0].split(","),
        api_stage=[
            output["OutputValue"]
            for output in stack["Outputs"]
            if output["OutputKey"] == "DeploymentStage"
        ][0],
        create_time=int(stack["CreationTime"].timestamp() * 1000),
    )


def delete_stack_by_bot_id(bot_id: str):
    client = boto3.client("cloudformation")
    stack_name = f"ApiPublishmentStack{bot_id}"
    response = client.delete_stack(StackName=stack_name)
    return response


# CodeBuild statuses of builds that are no longer running.
FINISHED_BUILD_STATUSES = frozenset(
    {"SUCCEEDED", "FAILED", "FAULT", "STOPPED", "TIMED_OUT"}
)


def is_build_running(build_id: str) -> bool:
    try:
        status = find_build_status_by_build_id(build_id)
    except RecordNotFoundError:
        # CodeBuild no longer keeps the build, so it has finished.
        return False
    return status not in FINISHED_BUILD_STATUSES


def find_build_status_by_build_id(build_id: str) -> str:
    client = boto3.client("codebuild")
    response = client.batch_get_builds(ids=[build_id])
    if len(response["builds"]) == 0:
        raise RecordNotFoundError("Build not found.")
    return response["builds"][0]["buildStatus"]


def delete_published_api(bot_id: str) -> None:
    """Delete the API keys and the stack of a published API. Safe to repeat."""
    try:
        stack = find_stack_by_bot_id(bot_id)
    except RecordNotFoundError:
        logger.info("Bot %s has no published API stack.", bot_id)
        return

    # The keys are not part of the stack, so delete them first.
    if stack.api_usage_plan_id:
        try:
            usage_plan = find_usage_plan_by_id(stack.api_usage_plan_id)
        except RecordNotFoundError:
            # Deleted by an earlier attempt.
            usage_plan = None
        for key_id in usage_plan.key_ids if usage_plan else []:
            try:
                delete_api_key(key_id)
            except ClientError as e:
                if e.response["Error"]["Code"] != "NotFoundException":
                    raise

    delete_stack_by_bot_id(bot_id)
