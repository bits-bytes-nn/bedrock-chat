"""Published API routes, called directly.

app.main includes these routes only when PUBLISHED_API_ID is set at import time, so
the tests call the route functions with a fake request instead of a TestClient.
"""

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from app.routes import published_api
from app.routes.schemas.conversation import (
    ChatInput,
    Conversation,
    MessageOutput,
    TextContent,
)
from app.routes.schemas.published_api import (
    ChatInputWithoutBotId,
    MessageInputWithoutMessageId,
)
from app.user import User
from fastapi import HTTPException

MODEL = "claude-v4.5-sonnet"


def _request(bot_id: str = "bot1"):
    user = User.from_published_api_id(bot_id)
    return SimpleNamespace(state=SimpleNamespace(current_user=user))


def _chat_input() -> ChatInputWithoutBotId:
    return ChatInputWithoutBotId(
        conversation_id="conv1",
        message=MessageInputWithoutMessageId(
            content=[TextContent(content_type="text", body="hello")], model=MODEL
        ),
    )


@pytest.fixture
def sqs():
    with patch.object(published_api, "sqs_client") as client:
        yield client


@pytest.fixture
def bot():
    with patch.object(published_api, "find_bot_by_id") as find_bot:
        yield find_bot


def test_post_message_uses_bot_id_from_user(sqs, bot):
    with patch.object(published_api, "validate_model_is_available") as validate:
        response = published_api.post_message(_request("bot1"), _chat_input())

    bot.assert_called_once_with("bot1")
    validate.assert_called_once_with(MODEL, bot.return_value)
    queued = ChatInput.model_validate_json(
        sqs.send_message.call_args.kwargs["MessageBody"]
    )
    assert queued.bot_id == "bot1"
    assert queued.conversation_id == "conv1"
    assert queued.message.message_id == response.message_id
    assert response.conversation_id == "conv1"


def test_post_message_rejects_unavailable_model(sqs, bot):
    with patch.object(
        published_api,
        "validate_model_is_available",
        side_effect=PermissionError("not active"),
    ):
        with pytest.raises(PermissionError):
            published_api.post_message(_request(), _chat_input())

    sqs.send_message.assert_not_called()


def test_post_message_returns_500_when_queueing_fails(sqs, bot):
    sqs.send_message.side_effect = RuntimeError("queue is down")
    with patch.object(published_api, "validate_model_is_available"):
        with pytest.raises(HTTPException) as e:
            published_api.post_message(_request(), _chat_input())

    assert e.value.status_code == 500
    assert "queue is down" not in str(e.value.detail)


def _message(children: list[str]) -> MessageOutput:
    return MessageOutput(
        role="user",
        content=[TextContent(content_type="text", body="hi")],
        model=MODEL,
        children=children,
        feedback=None,
        used_chunks=None,
        parent=None,
        thinking_log=None,
    )


def _conversation(message_map: dict[str, MessageOutput]) -> Conversation:
    return Conversation(
        id="conv1",
        title="t",
        create_time=1.0,
        message_map=message_map,
        last_message_id="m1",
        bot_id="bot1",
        should_continue=False,
    )


@pytest.mark.parametrize(
    "message_map, detail",
    [
        pytest.param({}, "not found", id="no-input-message"),
        pytest.param({"m1": _message([])}, "not ready", id="no-response-yet"),
        pytest.param({"m1": _message(["m2"])}, "not found", id="response-missing"),
    ],
)
def test_get_message_returns_404(message_map, detail):
    with patch.object(
        published_api, "fetch_conversation", return_value=_conversation(message_map)
    ) as fetch:
        with pytest.raises(HTTPException) as e:
            published_api.get_message(_request("bot1"), "conv1", "m1")

    fetch.assert_called_once_with("PUBLISHED_API#bot1", "conv1")
    assert e.value.status_code == 404
    assert detail in e.value.detail


def test_get_message_returns_first_child():
    reply = _message([])
    conversation = _conversation({"m1": _message(["m2"]), "m2": reply})
    with patch.object(published_api, "fetch_conversation", return_value=conversation):
        output = published_api.get_message(_request(), "conv1", "m1")

    assert output.message == reply
    assert output.conversation_id == "conv1"
