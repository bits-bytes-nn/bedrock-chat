import json
import logging

from app.metrics import emit_chat_cost
from app.routes.schemas.conversation import ChatInput
from app.usecases.chat import chat
from app.user import User

logger = logging.getLogger(__name__)


def handler(event, context):
    """SQS consumer.
    This is used for async invocation for published api.
    """
    for record in event["Records"]:
        message_body = json.loads(record["body"])
        chat_input = ChatInput(**message_body)

        assert chat_input.bot_id is not None, "bot_id is required for published api"

        user = User.from_published_api_id(chat_input.bot_id)

        conversation, message = chat(
            user=user,
            chat_input=chat_input,
            on_stop=lambda result: emit_chat_cost(result["price"]),
        )
        logger.info(
            "Processed message: conversation_id=%s, message_id=%s",
            conversation.id,
            conversation.last_message_id,
        )

    return {"statusCode": 200, "body": json.dumps("Processing completed")}
