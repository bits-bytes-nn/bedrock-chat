import json
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from botocore.exceptions import ClientError

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

    def test_passes_through_bedrock_model_errors(self):
        sender = NotificationSender(
            endpoint_url="https://example.com/dev", connection_id="connection"
        )
        chat_input = SimpleNamespace(
            conversation_id="conversation",
            bot_id=None,
            message=SimpleNamespace(model="claude-v4.7-opus"),
        )
        error = ClientError(
            {"Error": {"Code": "AccessDeniedException", "Message": "No access"}},
            "ConverseStream",
        )

        with patch.object(websocket, "chat", side_effect=error):
            process_chat_input(
                user=None,  # type: ignore[arg-type]
                chat_input=chat_input,  # type: ignore[arg-type]
                notificator=sender,
            )

        gatewayapi = FakeGatewayApi()
        run_sender(sender, gatewayapi)

        self.assertEqual(gatewayapi.sent, [{"status": "ERROR", "reason": "No access"}])


if __name__ == "__main__":
    unittest.main()
