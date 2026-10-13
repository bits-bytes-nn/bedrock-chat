import json
import logging
import os

import boto3
from app.metrics import emit_metric
from app.repositories.common import RecordNotFoundError
from app.repositories.conversation import (
    find_conversation_by_id,
    store_failed_message,
)
from app.routes.schemas.conversation import ChatInput
from app.usecases.chat import ConversationTooLargeError, MessageTooLargeError, chat
from app.user import User
from botocore.exceptions import ClientError
from strands.types.exceptions import ContextWindowOverflowException

logger = logging.getLogger(__name__)

# Receives before SQS moves a message to the dead-letter queue
# (cdk/lib/api-publishment-stack.ts).
MAX_RECEIVE_COUNT = int(os.environ.get("MAX_RECEIVE_COUNT", "2"))
# Retrying these would fail again and bill the model again.
NON_RETRYABLE_ERRORS = (
    ValueError,
    PermissionError,
    RecordNotFoundError,
    ContextWindowOverflowException,
)
# Set by cdk/lib/api-publishment-stack.ts; the failed answers alarm is per API.
PUBLISHED_API_ID = os.environ.get("PUBLISHED_API_ID")
QUEUE_URL = os.environ.get("QUEUE_URL", "")
# A message to retry is received again after this delay instead of after the
# queue's visibility timeout, which is sized for the slowest answer.
RETRY_DELAY_SECONDS = 30

sqs_client = boto3.client("sqs")


def _failure_reason(error: Exception) -> str:
    # Fixed texts, so that clients never see internal details of an error.
    if isinstance(error, RecordNotFoundError):
        return "The bot or the conversation was not found."
    if isinstance(error, PermissionError):
        return "The bot is not available."
    if isinstance(error, MessageTooLargeError):
        return "The message is too large."
    if isinstance(error, ConversationTooLargeError):
        return "The conversation is too large. Start a new conversation."
    if isinstance(error, ContextWindowOverflowException):
        return "The conversation is too long for the model."
    if isinstance(error, ValueError):
        return "The request is invalid, or its model is not available."
    return "The answer could not be generated."


def _is_answered(user_id: str, conversation_id: str, message_id: str) -> bool:
    # A message is stored together with its answer.
    try:
        conversation = find_conversation_by_id(user_id, conversation_id)
    except RecordNotFoundError:
        return False
    return message_id in conversation.message_map


def handler(event, context):
    """SQS consumer.
    This is used for async invocation for published api.
    Returns the messages to retry as partial batch failures.
    """
    batch_item_failures = []
    for record in event["Records"]:
        message_body = json.loads(record["body"])
        chat_input = ChatInput(**message_body)

        assert chat_input.bot_id is not None, "bot_id is required for published api"

        user = User.from_published_api_id(chat_input.bot_id)
        message_id = chat_input.message.message_id or ""

        try:
            conversation, message = chat(user=user, chat_input=chat_input)
        except Exception as e:
            # A redelivered message is rejected because its id exists, and storing
            # related documents can fail after the answer; the client has the answer.
            if _is_answered(user.id, chat_input.conversation_id, message_id):
                logger.warning(
                    "Message %s is already answered", message_id, exc_info=True
                )
                continue
            final = (
                isinstance(e, NON_RETRYABLE_ERRORS)
                or int(record.get("attributes", {}).get("ApproximateReceiveCount", "1"))
                >= MAX_RECEIVE_COUNT
            )
            if not final:
                logger.warning("Retrying message %s", message_id, exc_info=True)
                try:
                    sqs_client.change_message_visibility(
                        QueueUrl=QUEUE_URL,
                        ReceiptHandle=record["receiptHandle"],
                        VisibilityTimeout=RETRY_DELAY_SECONDS,
                    )
                except ClientError:
                    # The retry would come only after the visibility timeout, which is
                    # sized for the slowest answer, so it fails like the last receive.
                    logger.exception("Failed to delay the retry of %s", message_id)
                else:
                    batch_item_failures.append({"itemIdentifier": record["messageId"]})
                    continue
            logger.exception("Failed to answer message %s", message_id)
            # Clients poll for the answer; tell them that none will come.
            store_failed_message(
                user.id,
                chat_input.conversation_id,
                message_id,
                _failure_reason(e),
            )
            emit_metric(
                "FailedAnswers",
                1,
                {"PublishedApiId": PUBLISHED_API_ID} if PUBLISHED_API_ID else None,
            )
            continue
        logger.info(
            "Processed message: conversation_id=%s, message_id=%s",
            conversation.id,
            conversation.last_message_id,
        )

    return {"batchItemFailures": batch_item_failures}
