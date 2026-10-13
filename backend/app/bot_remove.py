import logging
import os
from typing import Any

import boto3
from app.repositories.api_publication import delete_published_api
from app.repositories.common import compose_sk, decompose_sk
from app.repositories.conversation import delete_conversation_by_user_id
from app.user import User
from app.utils import (
    CUSTOM_BOT_STACK_PREFIX,
    delete_api_key_from_secret_manager,
    delete_s3_prefix,
)

DOCUMENT_BUCKET = os.environ.get("DOCUMENT_BUCKET", "bedrock-documents")
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "us-east-1")

s3_client = boto3.client("s3", BEDROCK_REGION)

logger = logging.getLogger(__name__)


def delete_custom_bot_stack_by_bot_id(bot_id: str):
    client = boto3.client("cloudformation", BEDROCK_REGION)
    # DeleteStack succeeds when the stack does not exist.
    return client.delete_stack(StackName=f"{CUSTOM_BOT_STACK_PREFIX}{bot_id}")


def delete_from_s3(user_id: str, bot_id: str):
    """Delete all files in S3 bucket for the specified `user_id` and `bot_id`."""
    delete_s3_prefix(s3_client, DOCUMENT_BUCKET, f"{user_id}/{bot_id}/")
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
    if not sk or not sk.startswith(compose_sk("", "bot")):
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
        lambda: delete_published_api(bot_id),
        lambda: delete_from_s3(user_id, bot_id),
        lambda: delete_api_key_from_secret_manager(user_id, bot_id, "firecrawl"),
        # Last, because it can take long: the conversations of the API's clients,
        # stored under the API's own user. A retry continues where it stopped.
        lambda: delete_conversation_by_user_id(User.from_published_api_id(bot_id).id),
    ):
        try:
            step()
        except Exception as e:
            logger.exception("Failed to clean up bot %s", bot_id)
            errors.append(e)
    if errors:
        raise errors[0]
