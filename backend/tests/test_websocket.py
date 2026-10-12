import json
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_aws

sys.path.insert(0, ".")
os.environ.setdefault("WEBSOCKET_SESSION_TABLE_NAME", "test-websocket-session")

from app import websocket
from app.websocket import NotificationSender, process_chat_input


class _GoneException(Exception):
    pass


class _ForbiddenException(Exception):
    pass


class FakeGatewayApi:
    def __init__(self, fail_with: Exception | None = None) -> None:
        self.exceptions = SimpleNamespace(
            GoneException=_GoneException,
            ForbiddenException=_ForbiddenException,
        )
        self.sent: list[dict] = []
        self.fail_with = fail_with

    def post_to_connection(self, ConnectionId: str, Data: bytes) -> None:
        if self.fail_with is not None:
            raise self.fail_with
        self.sent.append(json.loads(Data))


def run_sender(sender: NotificationSender, gatewayapi: FakeGatewayApi) -> None:
    sender.finish()
    with patch.object(websocket.boto3, "client", return_value=gatewayapi):
        sender.run()


class TestNotificationSender(unittest.TestCase):
    def setUp(self) -> None:
        self.sender = NotificationSender(
            endpoint_url="https://example.com/dev", connection_id="connection"
        )

    def test_merges_queued_completions_and_keeps_order(self):
        self.sender.on_reasoning("think ")
        self.sender.on_reasoning("more")
        self.sender.on_stream("Hello")
        self.sender.on_stream(", ")
        self.sender.on_stream("world")
        self.sender.notify(json.dumps({"status": "AGENT_THINKING"}).encode())
        self.sender.on_stream("!")

        gatewayapi = FakeGatewayApi()
        run_sender(self.sender, gatewayapi)

        self.assertEqual(
            gatewayapi.sent,
            [
                {"status": "REASONING", "completion": "think more"},
                {"status": "STREAMING", "completion": "Hello, world"},
                {"status": "AGENT_THINKING"},
                {"status": "STREAMING", "completion": "!"},
            ],
        )

    def test_limits_merged_completion_size(self):
        token = "a" * 1024
        token_count = websocket.MAX_MERGED_COMPLETION_CHARS // len(token) + 1
        for _ in range(token_count):
            self.sender.on_stream(token)

        gatewayapi = FakeGatewayApi()
        run_sender(self.sender, gatewayapi)

        completions = [message["completion"] for message in gatewayapi.sent]
        self.assertEqual(len(completions), 2)
        self.assertEqual("".join(completions), token * token_count)

    def test_stops_when_connection_is_gone(self):
        self.sender.on_stream("lost")
        gatewayapi = FakeGatewayApi(fail_with=_GoneException())

        run_sender(self.sender, gatewayapi)

        self.assertEqual(gatewayapi.sent, [])

    def test_error_is_not_sent_after_stream_end(self):
        self.sender.on_stop(
            {
                "message": None,  # type: ignore[typeddict-item]
                "stop_reason": "end_turn",
                "input_token_count": 1,
                "output_token_count": 1,
                "cache_read_input_count": 0,
                "cache_write_input_count": 0,
                "price": 0.0,
            }
        )
        self.sender.on_error("failed after the response")

        gatewayapi = FakeGatewayApi()
        run_sender(self.sender, gatewayapi)

        self.assertEqual(
            [message["status"] for message in gatewayapi.sent], ["STREAMING_END"]
        )


class TestProcessChatInput(unittest.TestCase):
    def test_pushes_error_to_connection(self):
        sender = NotificationSender(
            endpoint_url="https://example.com/dev", connection_id="connection"
        )
        chat_input = SimpleNamespace(
            conversation_id="conversation",
            bot_id=None,
            message=SimpleNamespace(model="claude-v4.7-opus"),
        )

        with patch.object(websocket, "chat", side_effect=RuntimeError("boom")):
            response = process_chat_input(
                user=None,  # type: ignore[arg-type]
                chat_input=chat_input,  # type: ignore[arg-type]
                notificator=sender,
            )

        gatewayapi = FakeGatewayApi()
        run_sender(sender, gatewayapi)

        self.assertEqual(response["statusCode"], 500)
        self.assertEqual(
            gatewayapi.sent,
            [{"status": "ERROR", "reason": "Failed to generate the answer."}],
        )

    def bedrock_error_reason(self, code: str, message: str) -> str:
        sender = NotificationSender(
            endpoint_url="https://example.com/dev", connection_id="connection"
        )
        chat_input = SimpleNamespace(
            conversation_id="conversation",
            bot_id=None,
            message=SimpleNamespace(model="claude-v4.7-opus"),
        )
        error = ClientError(
            {"Error": {"Code": code, "Message": message}}, "ConverseStream"
        )

        with patch.object(websocket, "chat", side_effect=error):
            process_chat_input(
                user=None,  # type: ignore[arg-type]
                chat_input=chat_input,  # type: ignore[arg-type]
                notificator=sender,
            )

        gatewayapi = FakeGatewayApi()
        run_sender(sender, gatewayapi)
        return gatewayapi.sent[0]["reason"]

    def test_passes_through_bedrock_model_errors(self):
        self.assertEqual(
            self.bedrock_error_reason("ValidationException", "Input is too long"),
            "Input is too long",
        )

    def test_hides_access_denied_details(self):
        reason = self.bedrock_error_reason(
            "AccessDeniedException",
            "User: arn:aws:sts::123456789012:assumed-role/x is not authorized",
        )
        self.assertNotIn("arn:aws", reason)


@pytest.fixture
def session_table():
    with mock_aws():
        boto3.client("dynamodb", region_name="us-east-1").create_table(
            TableName=os.environ["WEBSOCKET_SESSION_TABLE_NAME"],
            BillingMode="PAY_PER_REQUEST",
            AttributeDefinitions=[
                {"AttributeName": "ConnectionId", "AttributeType": "S"},
                {"AttributeName": "MessagePartId", "AttributeType": "N"},
            ],
            KeySchema=[
                {"AttributeName": "ConnectionId", "KeyType": "HASH"},
                {"AttributeName": "MessagePartId", "KeyType": "RANGE"},
            ],
        )
        session_table = boto3.resource("dynamodb", region_name="us-east-1").Table(
            os.environ["WEBSOCKET_SESSION_TABLE_NAME"]
        )
        with patch.object(websocket, "table", session_table):
            yield


def frame(body: dict, connection_id: str = "connection") -> dict:
    return {
        "requestContext": {
            "routeKey": "$default",
            "connectionId": connection_id,
            "domainName": "example.com",
            "stage": "dev",
        },
        "body": json.dumps(body),
    }


CHAT_INPUT = {
    "conversationId": "conversation",
    "message": {
        "role": "user",
        "content": [{"contentType": "text", "body": "hello"}],
        "model": "claude-v5.5-haiku",
        "parentMessageId": None,
    },
    "botId": None,
}
TOKEN = {"sub": "user", "cognito:username": "user", "email": "user@example.com"}


@pytest.mark.usefixtures("session_table")
class TestHandler:
    def start(self, sub: str = "user"):
        with patch.object(
            websocket, "verify_token", return_value={**TOKEN, "sub": sub}
        ):
            return websocket.handler(frame({"step": "START", "token": "t"}), None)

    def end(self, sub: str = "user"):
        with (
            patch.object(websocket, "verify_token", return_value={**TOKEN, "sub": sub}),
            patch.object(
                websocket, "_process_with_sender", return_value={"statusCode": 200}
            ) as process,
        ):
            response = websocket.handler(frame({"step": "END", "token": "t"}), None)
        return response, process

    def test_reassembles_parts_in_order(self):
        payload = json.dumps(CHAT_INPUT)
        self.start()
        for index, part in reversed(list(enumerate([payload[:20], payload[20:]]))):
            response = websocket.handler(
                frame({"step": "BODY", "index": index, "part": part}), None
            )
            assert response["statusCode"] == 200

        response, process = self.end()

        assert response["statusCode"] == 200
        chat_input = process.call_args.args[4]
        assert chat_input.message.content[0].body == "hello"

    def test_rejects_parts_without_a_session(self):
        response = websocket.handler(
            frame({"step": "BODY", "index": 0, "part": "x"}), None
        )
        assert response["statusCode"] == 403

    @pytest.mark.parametrize(
        "body",
        [
            {"step": "BODY", "index": -1, "part": "x"},
            {"step": "BODY", "index": websocket.MAX_MESSAGE_PARTS, "part": "x"},
            {"step": "BODY", "index": "0", "part": "x"},
            {
                "step": "BODY",
                "index": 0,
                "part": "x" * (websocket.MAX_MESSAGE_PART_CHARS + 1),
            },
        ],
    )
    def test_rejects_invalid_parts(self, body):
        self.start()
        assert websocket.handler(frame(body), None)["statusCode"] == 400

    def test_rejects_end_from_another_user(self):
        self.start(sub="user")
        response, process = self.end(sub="someone-else")

        assert response["statusCode"] == 403
        process.assert_not_called()


if __name__ == "__main__":
    unittest.main()
