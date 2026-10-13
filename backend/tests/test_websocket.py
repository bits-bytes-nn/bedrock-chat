import json
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import boto3
import pytest
from botocore.exceptions import ClientError
from strands.types.exceptions import ModelThrottledException
from moto import mock_aws

sys.path.insert(0, ".")
os.environ.setdefault("WEBSOCKET_SESSION_TABLE_NAME", "test-websocket-session")

from app import websocket
from app.metrics import emit_chat_cost
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
        self.sender.on_error("failed after the response", "generation_failed")

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
            [
                {
                    "status": "ERROR",
                    "reason": "Failed to generate the answer.",
                    "code": "generation_failed",
                }
            ],
        )

    def bedrock_error(self, code: str, message: str) -> dict:
        return self.error_frame(
            ClientError({"Error": {"Code": code, "Message": message}}, "ConverseStream")
        )

    def error_frame(self, error: Exception) -> dict:
        sender = NotificationSender(
            endpoint_url="https://example.com/dev", connection_id="connection"
        )
        chat_input = SimpleNamespace(
            conversation_id="conversation",
            bot_id=None,
            message=SimpleNamespace(model="claude-v4.7-opus"),
        )

        with patch.object(websocket, "chat", side_effect=error):
            process_chat_input(
                user=None,  # type: ignore[arg-type]
                chat_input=chat_input,  # type: ignore[arg-type]
                notificator=sender,
            )

        gatewayapi = FakeGatewayApi()
        run_sender(sender, gatewayapi)
        return gatewayapi.sent[0]

    def test_passes_through_bedrock_model_errors(self):
        frame = self.bedrock_error("ValidationException", "Input is too long")
        self.assertEqual(frame["reason"], "Input is too long")
        self.assertEqual(frame["code"], "model_error")

    def test_reports_throttling(self):
        frame = self.error_frame(ModelThrottledException("Too many requests"))
        self.assertIn("busy", frame["reason"])
        self.assertEqual(frame["code"], "throttled")

    def test_hides_access_denied_details(self):
        frame = self.bedrock_error(
            "AccessDeniedException",
            "User: arn:aws:sts::123456789012:assumed-role/x is not authorized",
        )
        self.assertNotIn("arn:aws", frame["reason"])
        self.assertEqual(frame["code"], "model_unavailable")


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

    def send_parts(self, parts: dict[int, str]) -> None:
        for index, part in parts.items():
            response = websocket.handler(
                frame({"step": "BODY", "index": index, "part": part}), None
            )
            assert response["statusCode"] == 200

    MALFORMED_MESSAGES = [
        pytest.param(
            {0: json.dumps(CHAT_INPUT)[:20], 2: json.dumps(CHAT_INPUT)[40:]},
            id="gap-in-part-indexes",
        ),
        pytest.param({}, id="no-parts"),
        pytest.param({0: "{not json"}, id="invalid-json"),
        pytest.param({0: json.dumps({"message": "hi"})}, id="not-a-chat-input"),
    ]

    @pytest.mark.parametrize("parts", MALFORMED_MESSAGES)
    def test_malformed_message_is_rejected(self, parts):
        self.start()
        self.send_parts(parts)

        response, process = self.end()

        assert response["statusCode"] == 400
        assert json.loads(response["body"])["status"] == "ERROR"
        process.assert_not_called()


class TestChatCostMetric(unittest.TestCase):
    # app.metrics, used by the chat and published API handlers.
    def test_emits_the_price_in_embedded_metric_format(self):
        import io
        from contextlib import redirect_stdout

        out = io.StringIO()
        with redirect_stdout(out):
            emit_chat_cost(0.25)
        line = json.loads(out.getvalue())
        metric = line["_aws"]["CloudWatchMetrics"][0]
        self.assertEqual(metric["Namespace"], "BedrockChat")
        self.assertEqual(metric["Metrics"][0]["Name"], "ChatCost")
        self.assertEqual(line["ChatCost"], 0.25)


if __name__ == "__main__":
    unittest.main()
