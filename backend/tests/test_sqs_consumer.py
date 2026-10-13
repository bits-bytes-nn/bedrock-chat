import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app import sqs_consumer
from app.repositories.common import RecordNotFoundError
from app.usecases.chat import ConversationTooLargeError
from botocore.exceptions import ClientError
from strands.types.exceptions import ContextWindowOverflowException


class TestSqsConsumer(unittest.TestCase):
    def handle(
        self,
        error: Exception,
        receive_count: int,
        stored: object = RecordNotFoundError("x"),
        visibility_error: Exception | None = None,
    ):
        record = {
            "messageId": "sqs-1",
            "receiptHandle": "receipt-1",
            "body": json.dumps(self.body()),
            "attributes": {"ApproximateReceiveCount": str(receive_count)},
        }
        find = (
            {"side_effect": stored}
            if isinstance(stored, Exception)
            else {"return_value": stored}
        )
        with (
            patch.object(sqs_consumer, "chat", side_effect=error),
            patch.object(sqs_consumer, "find_conversation_by_id", **find),
            patch.object(sqs_consumer, "store_failed_message") as store,
            patch.object(sqs_consumer, "PUBLISHED_API_ID", "bot"),
            patch.object(sqs_consumer, "QUEUE_URL", "queue"),
            patch.object(sqs_consumer, "sqs_client") as self.sqs,
            patch.object(sqs_consumer, "emit_metric") as self.emit,
        ):
            self.sqs.change_message_visibility.side_effect = visibility_error
            self.response = sqs_consumer.handler({"Records": [record]}, None)
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

    def test_retries_transient_errors_soon_before_the_last_receive(self):
        store = self.handle(RuntimeError("throttled"), receive_count=1)
        self.assertEqual(
            self.response, {"batchItemFailures": [{"itemIdentifier": "sqs-1"}]}
        )
        self.sqs.change_message_visibility.assert_called_once_with(
            QueueUrl="queue",
            ReceiptHandle="receipt-1",
            VisibilityTimeout=sqs_consumer.RETRY_DELAY_SECONDS,
        )
        store.assert_not_called()
        self.emit.assert_not_called()

    def test_records_the_failure_on_the_last_receive(self):
        store = self.handle(RuntimeError("throttled"), receive_count=2)
        store.assert_called_once_with(
            "PUBLISHED_API#bot", "c", "m", "The answer could not be generated."
        )
        self.emit.assert_called_once_with("FailedAnswers", 1, {"PublishedApiId": "bot"})
        self.assertEqual(self.response, {"batchItemFailures": []})
        self.sqs.change_message_visibility.assert_not_called()

    def test_records_the_failure_when_the_retry_cannot_be_delayed(self):
        error = ClientError(
            {"Error": {"Code": "ReceiptHandleIsInvalid", "Message": "x"}},
            "ChangeMessageVisibility",
        )
        store = self.handle(
            RuntimeError("throttled"), receive_count=1, visibility_error=error
        )
        store.assert_called_once_with(
            "PUBLISHED_API#bot", "c", "m", "The answer could not be generated."
        )
        self.emit.assert_called_once()
        self.assertEqual(self.response, {"batchItemFailures": []})

    def test_does_not_retry_inputs_that_are_too_large(self):
        for error, reason in (
            (
                ConversationTooLargeError("x"),
                "The conversation is too large. Start a new conversation.",
            ),
            (
                ContextWindowOverflowException("x"),
                "The conversation is too long for the model.",
            ),
        ):
            store = self.handle(error, receive_count=1)
            store.assert_called_once_with("PUBLISHED_API#bot", "c", "m", reason)
            self.sqs.change_message_visibility.assert_not_called()

    def test_does_not_retry_errors_that_would_fail_again(self):
        store = self.handle(ValueError("Model is not available."), receive_count=1)
        store.assert_called_once_with(
            "PUBLISHED_API#bot",
            "c",
            "m",
            "The request is invalid, or its model is not available.",
        )
        self.assertEqual(self.response, {"batchItemFailures": []})

    def test_does_not_record_a_failure_for_a_message_that_is_answered(self):
        # A redelivered message is rejected because its id exists.
        answered = SimpleNamespace(message_map={"m": object()})
        store = self.handle(
            ValueError("Message id m already exists."),
            receive_count=2,
            stored=answered,
        )
        store.assert_not_called()
        self.emit.assert_not_called()
        self.assertEqual(self.response, {"batchItemFailures": []})
