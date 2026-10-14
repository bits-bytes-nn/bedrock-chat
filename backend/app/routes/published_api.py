import logging
import os

import boto3
from app.repositories.common import RecordNotFoundError
from app.repositories.conversation import find_failed_message
from app.routes.schemas.conversation import (
    ChatInput,
    Conversation,
    MessageInput,
    MessageOutput,
)
from app.routes.schemas.published_api import (
    ChatInputWithoutBotId,
    ChatOutputWithoutBotId,
    MessageRequestedResponse,
)
from app.repositories.custom_bot import find_bot_by_id
from app.usecases.chat import fetch_conversation, validate_model_is_available
from app.user import User
from botocore.exceptions import ClientError
from fastapi import APIRouter, HTTPException, Request
from ulid import ULID

logger = logging.getLogger(__name__)

router = APIRouter(tags=["published_api"])

sqs_client = boto3.client("sqs")
QUEUE_URL = os.environ.get("QUEUE_URL", "")
# app.main includes this router only when PUBLISHED_API_ID is set.
PUBLISHED_API_ID = os.environ.get("PUBLISHED_API_ID", "")


@router.get("/health")
def health():
    """For health check"""
    return {"status": "ok"}


@router.post("/conversation", response_model=MessageRequestedResponse)
def post_message(request: Request, message_input: ChatInputWithoutBotId):
    """Send chat message"""
    if message_input.continue_generate:
        # The continued answer replaces the previous one instead of answering the
        # returned message id, so clients would poll for it forever.
        raise HTTPException(
            status_code=400,
            detail="continueGenerate is not supported by the published API.",
        )

    # The published API serves one bot; its id is the published API id.
    bot_id = PUBLISHED_API_ID

    # Generate conversation id if not provided
    conversation_id = (
        str(ULID())
        if message_input.conversation_id is None
        else message_input.conversation_id
    )
    # Issue id for the response message
    response_message_id = str(ULID())

    # Reject unavailable models now instead of failing later in the queue consumer.
    validate_model_is_available(message_input.message.model, find_bot_by_id(bot_id))

    chat_input = ChatInput(
        conversation_id=conversation_id,
        message=MessageInput(
            role="user",
            content=message_input.message.content,
            model=message_input.message.model,
            parent_message_id=None,  # Use the latest message as the parent
            message_id=response_message_id,
        ),
        bot_id=bot_id,
        continue_generate=message_input.continue_generate,
        enable_reasoning=message_input.enable_reasoning,
    )

    try:
        _ = sqs_client.send_message(
            QueueUrl=QUEUE_URL, MessageBody=chat_input.model_dump_json()
        )
    except Exception as e:
        error = e.response.get("Error", {}) if isinstance(e, ClientError) else {}
        # SQS rejects a body over the queue's maximum message size with this error.
        if error.get("Code") == "InvalidParameterValue" and (
            "Message must be shorter than" in error.get("Message", "")
        ):
            raise HTTPException(
                status_code=413,
                detail="The message is too large to queue. Send smaller attachments.",
            )
        logger.exception("Failed to queue the message")
        raise HTTPException(status_code=500, detail="Failed to queue the message.")

    return MessageRequestedResponse(
        conversation_id=conversation_id, message_id=response_message_id
    )


@router.get("/conversation/{conversation_id}", response_model=Conversation)
def get_conversation(request: Request, conversation_id: str):
    """Get a conversation history. If the conversation does not exist, it will return 404."""
    current_user: User = request.state.current_user

    output = fetch_conversation(current_user.id, conversation_id)
    return output


def _find_answer(conversation: Conversation, message_id: str) -> MessageOutput | None:
    input_message = conversation.message_map.get(message_id)
    if input_message is None or not input_message.children:
        return None
    return conversation.message_map.get(input_message.children[0])


@router.get(
    "/conversation/{conversation_id}/{message_id}",
    response_model=ChatOutputWithoutBotId,
)
def get_message(request: Request, conversation_id: str, message_id: str):
    """Get specified message in a conversation. If the message does not exist, it will return 404."""
    current_user: User = request.state.current_user

    try:
        conversation = fetch_conversation(current_user.id, conversation_id)
    except RecordNotFoundError:
        # The first message of a conversation can fail before anything is stored.
        conversation = None

    # A stored answer wins over a failure that was recorded after storing it.
    if conversation is not None:
        answer = _find_answer(conversation, message_id)
        if answer is not None:
            return ChatOutputWithoutBotId(
                conversation_id=conversation_id,
                message=answer,
                create_time=conversation.create_time,
            )

    reason = find_failed_message(current_user.id, conversation_id, message_id)
    if reason is not None:
        raise HTTPException(status_code=500, detail=reason)

    if conversation is None:
        raise RecordNotFoundError(f"No conversation found with id: {conversation_id}")
    # A message is stored together with its answer, so it is missing until then.
    raise HTTPException(
        status_code=404,
        detail=f"No answer to message {message_id} in conversation {conversation_id} yet",
    )
