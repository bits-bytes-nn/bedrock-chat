import json
import unittest
from unittest.mock import MagicMock, patch

from app import sqs_consumer


class TestSqsConsumer(unittest.TestCase):
    def test_published_api_answers_count_toward_the_chat_cost(self):
        def answer(user, chat_input, on_stop):
            on_stop({"price": 0.5})
            return MagicMock(id="c", last_message_id="m"), MagicMock()

        body = {
            "conversationId": "c",
            "botId": "bot",
            "message": {
                "role": "user",
                "content": [{"contentType": "text", "body": "hi"}],
                "model": "claude-v5.5-haiku",
                "parentMessageId": None,
            },
        }
        with patch.object(sqs_consumer, "chat", side_effect=answer), patch.object(
            sqs_consumer, "emit_chat_cost"
        ) as emit:
            sqs_consumer.handler({"Records": [{"body": json.dumps(body)}]}, None)
        emit.assert_called_once_with(0.5)

    def handle(self, error: Exception, receive_count: int):
        record = {
            "body": json.dumps(self.body()),
            "attributes": {"ApproximateReceiveCount": str(receive_count)},
        }
        with patch.object(sqs_consumer, "chat", side_effect=error), patch.object(
            sqs_consumer, "store_failed_message"
        ) as store:
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

    def test_records_the_failure_on_the_last_receive(self):
        store = self.handle(RuntimeError("throttled"), receive_count=2)
        store.assert_called_once_with(
            "PUBLISHED_API#bot", "c", "m", "The answer could not be generated."
        )

    def test_does_not_retry_errors_that_would_fail_again(self):
        store = self.handle(ValueError("Model is not available."), receive_count=1)
        store.assert_called_once_with(
            "PUBLISHED_API#bot", "c", "m", "Model is not available."
        )
