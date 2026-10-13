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
