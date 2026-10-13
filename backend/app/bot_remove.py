import logging
import os
from typing import Any

import boto3
from botocore.exceptions import ClientError
from app.repositories.api_publication import (
    delete_api_key,
    delete_stack_by_bot_id,
    find_stack_by_bot_id,
    find_usage_plan_by_id,
)
from app.repositories.common import RecordNotFoundError, decompose_sk
from app.utils import delete_api_key_from_secret_manager

DOCUMENT_BUCKET = os.environ.get("DOCUMENT_BUCKET", "bedrock-documents")
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
    """Bot removal handler, triggered by the DynamoDB stream when a bot is deleted.

    Deletes the knowledge base stack, the published API stack and its API keys, the
    bot's S3 files and its Firecrawl secret.
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

    # Every step runs even if another fails, and the failure is raised at the end so
    # that the stream retries the record. Each step is idempotent. Stacks go first:
    # a leaked knowledge base stack keeps an OpenSearch Serverless collection billing.
    errors: list[Exception] = []
    for step in (
        lambda: delete_custom_bot_stack_by_bot_id(bot_id),
        lambda: _delete_published_api(bot_id),
        lambda: delete_from_s3(user_id, bot_id),
        lambda: delete_api_key_from_secret_manager(user_id, bot_id, "firecrawl"),
    ):
        try:
            step()
        except Exception as e:
            logger.exception("Failed to clean up bot %s", bot_id)
            errors.append(e)
    if errors:
        raise errors[0]


def _delete_published_api(bot_id: str) -> None:
    try:
        stack = find_stack_by_bot_id(bot_id)
    except RecordNotFoundError:
        logger.info("Bot %s has no published API stack.", bot_id)
        return

    # Before delete cfn stack, delete all api keys
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

    # Delete `ApiPublishmentStack` by CloudFormation
    delete_stack_by_bot_id(bot_id)
