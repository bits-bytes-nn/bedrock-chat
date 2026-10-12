import logging
import os
from typing import Any

import boto3
from app.repositories.api_publication import (
    delete_api_key,
    delete_stack_by_bot_id,
    find_stack_by_bot_id,
    find_usage_plan_by_id,
)
from app.repositories.common import RecordNotFoundError, decompose_sk
from app.utils import delete_api_key_from_secret_manager

DOCUMENT_BUCKET = os.environ.get("DOCUMENT_BUCKET", "documents")
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "us-east-1")

s3_client = boto3.client("s3", BEDROCK_REGION)

logger = logging.getLogger(__name__)


def delete_custom_bot_stack_by_bot_id(bot_id: str):
    client = boto3.client("cloudformation", BEDROCK_REGION)
    # DeleteStack succeeds when the stack does not exist.
    return client.delete_stack(StackName=f"BrChatKbStack{bot_id}")


def delete_from_s3(user_id: str, bot_id: str):
    """Delete all files in S3 bucket for the specified `user_id` and `bot_id`."""
    prefix = f"{user_id}/{bot_id}/"
    paginator = s3_client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=DOCUMENT_BUCKET, Prefix=prefix):
        keys = [{"Key": obj["Key"]} for obj in page.get("Contents", [])]
        if keys:
            s3_client.delete_objects(Bucket=DOCUMENT_BUCKET, Delete={"Objects": keys})
    logger.info("Deleted the S3 files of bot %s", bot_id)


def handler(event: dict, context: Any) -> None:
    """Bot removal handler.
    This function is triggered by dynamodb stream when item is deleted.
    Following resources are deleted asynchronously when bot is deleted:
    - vector store record (postgres)
    - s3 files
    - cloudformation stack (if exists)
    """

    # NOTE: batch size is 1
    record = event["Records"][0]

    pk = record["dynamodb"]["Keys"]["PK"]["S"]
    sk = record["dynamodb"]["Keys"].get("SK", {}).get("S")
    if not sk or "BOT#" not in sk:
        # Ignore non-bot items
        logger.info("Skipping event for SK: %s", sk)
        return

    user_id = pk
    bot_id = decompose_sk(sk)

    delete_from_s3(user_id, bot_id)
    delete_custom_bot_stack_by_bot_id(bot_id)
    delete_api_key_from_secret_manager(user_id, bot_id, "firecrawl")

    # Check if api published stack exists
    try:
        stack = find_stack_by_bot_id(bot_id)
    except RecordNotFoundError:
        logger.info("Bot %s has no published API stack.", bot_id)
        return

    # Before delete cfn stack, delete all api keys
    if stack.api_usage_plan_id:  # Add type check
        usage_plan = find_usage_plan_by_id(stack.api_usage_plan_id)
        for key_id in usage_plan.key_ids:
            delete_api_key(key_id)

    # Delete `ApiPublishmentStack` by CloudFormation
    delete_stack_by_bot_id(bot_id)
