import json
import logging
import os

from app.metrics import emit_metric
from app.repositories.common import RecordNotFoundError
from app.repositories.conversation import store_failed_message
from app.routes.schemas.conversation import ChatInput
from app.usecases.chat import chat
from app.user import User

logger = logging.getLogger(__name__)

# Receives before SQS moves a message to the dead-letter queue
# (cdk/lib/api-publishment-stack.ts).
MAX_RECEIVE_COUNT = int(os.environ.get("MAX_RECEIVE_COUNT", "2"))
# Retrying these would fail again and bill the model again.
NON_RETRYABLE_ERRORS = (ValueError, PermissionError, RecordNotFoundError)
# Set by cdk/lib/api-publishment-stack.ts; the failed answers alarm is per API.
PUBLISHED_API_ID = os.environ.get("PUBLISHED_API_ID")


def _failure_reason(error: Exception) -> str:
    # Fixed texts, so that clients never see internal details of an error.
    if isinstance(error, RecordNotFoundError):
        return "The bot or the conversation was not found."
    if isinstance(error, PermissionError):
        return "The bot is not available."
    if isinstance(error, ValueError):
        return "The request is invalid, or its model is not available."
    return "The answer could not be generated."


def handler(event, context):
    """SQS consumer.
    This is used for async invocation for published api.
    """
    for record in event["Records"]:
        message_body = json.loads(record["body"])
        chat_input = ChatInput(**message_body)

        assert chat_input.bot_id is not None, "bot_id is required for published api"

        user = User.from_published_api_id(chat_input.bot_id)
        message_id = chat_input.message.message_id or ""

        try:
            conversation, message = chat(user=user, chat_input=chat_input)
        except Exception as e:
            final = (
                isinstance(e, NON_RETRYABLE_ERRORS)
                or int(record.get("attributes", {}).get("ApproximateReceiveCount", "1"))
                >= MAX_RECEIVE_COUNT
            )
            if not final:
                raise
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

    return {"statusCode": 200, "body": json.dumps("Processing completed")}
