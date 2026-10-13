import json
import unittest
from unittest.mock import patch

from app import sqs_consumer


class TestSqsConsumer(unittest.TestCase):
    def handle(self, error: Exception, receive_count: int):
        record = {
            "body": json.dumps(self.body()),
            "attributes": {"ApproximateReceiveCount": str(receive_count)},
        }
        with (
            patch.object(sqs_consumer, "chat", side_effect=error),
            patch.object(sqs_consumer, "store_failed_message") as store,
            patch.object(sqs_consumer, "PUBLISHED_API_ID", "bot"),
            patch.object(sqs_consumer, "emit_metric") as self.emit,
        ):
            sqs_consumer.handler({"Records": [record]}, None)
        return store

    def body(self) -> dict:
        return {
            "conversationId": "c",
            "botId": "bot",
            "message": {
                "role": "user",
                "content": [{"contentType": "text", "body": "hi"}],
                "model": "claude-v5.5-haiku",
                "parentMessageId": None,
                "messageId": "m",
            },
        }

    def test_retries_transient_errors_before_the_last_receive(self):
        with self.assertRaises(RuntimeError):
            self.handle(RuntimeError("throttled"), receive_count=1)
        self.emit.assert_not_called()

    def test_records_the_failure_on_the_last_receive(self):
        store = self.handle(RuntimeError("throttled"), receive_count=2)
        store.assert_called_once_with(
            "PUBLISHED_API#bot", "c", "m", "The answer could not be generated."
        )
        self.emit.assert_called_once_with("FailedAnswers", 1, {"PublishedApiId": "bot"})

    def test_does_not_retry_errors_that_would_fail_again(self):
        store = self.handle(ValueError("Model is not available."), receive_count=1)
        store.assert_called_once_with(
            "PUBLISHED_API#bot",
            "c",
            "m",
            "The request is invalid, or its model is not available.",
        )
