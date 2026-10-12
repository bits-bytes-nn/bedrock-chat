import unittest
from unittest.mock import patch

import pytest
from app.repositories.conversation import find_conversation_by_id
from app.repositories.models.conversation import MessageModel, TextContentModel
from app.routes.schemas.conversation import ChatInput
from app.stream import OnStopInput
from app.usecases import chat as chat_usecase
from app.user import User

USER = User(id="user", name="user", email="user@example.com", groups=[])
MODEL = "claude-v5.5-haiku"


def answer(text: str) -> OnStopInput:
    return {
        "message": MessageModel(
            role="assistant",
            content=[TextContentModel(content_type="text", body=text)],
            model=MODEL,
            children=[],
            parent=None,
            create_time=0,
            feedback=None,
            used_chunks=None,
            thinking_log=None,
        ),
        "stop_reason": "end_turn",
        "input_token_count": 10,
        "output_token_count": 5,
        "cache_read_input_count": 0,
        "cache_write_input_count": 0,
        "price": 0.5,
    }


def chat_input(conversation_id: str, parent: str | None, text: str) -> ChatInput:
    return ChatInput.model_validate(
        {
            "conversation_id": conversation_id,
            "message": {
                "role": "user",
                "content": [{"content_type": "text", "body": text}],
                "model": MODEL,
                "parent_message_id": parent,
            },
        }
    )


@pytest.mark.usefixtures("dynamodb_tables")
class TestChatFlow(unittest.TestCase):
    """Runs chat() against DynamoDB with the model call stubbed."""

    def send(self, conversation_id: str, parent: str | None, text: str):
        with patch.object(
            chat_usecase, "converse_with_strands", return_value=answer(f"re: {text}")
        ) as converse:
            conversation, message = chat_usecase.chat(
                USER, chat_input(conversation_id, parent, text)
            )
        return conversation, message, converse.call_args.kwargs["messages"]

    def test_first_and_continued_messages(self):
        _, _, sent = self.send("c1", None, "hello")
        self.assertEqual([m.role for m in sent], ["system", "user"])

        stored = find_conversation_by_id(USER.id, "c1")
        first_answer = stored.last_message_id
        self.assertEqual(stored.total_price, 0.5)
        user_msg_id = stored.message_map[first_answer].parent
        self.assertEqual(stored.message_map[user_msg_id].parent, "system")
        self.assertEqual(stored.message_map["system"].children, [user_msg_id])

        _, _, sent = self.send("c1", first_answer, "again")
        # The model sees the whole branch, not only the new message.
        self.assertEqual(
            [m.role for m in sent], ["system", "user", "assistant", "user"]
        )

        stored = find_conversation_by_id(USER.id, "c1")
        self.assertEqual(stored.total_price, 1.0)
        second_user = stored.message_map[stored.last_message_id].parent
        self.assertEqual(stored.message_map[second_user].parent, first_answer)

    def test_regenerate_adds_a_sibling_branch(self):
        self.send("c2", None, "hello")

        # Regenerating resends the user turn under the same parent.
        _, _, sent = self.send("c2", "system", "hello")
        self.assertEqual([m.role for m in sent], ["system", "user"])

        stored = find_conversation_by_id(USER.id, "c2")
        self.assertEqual(len(stored.message_map["system"].children), 2)


if __name__ == "__main__":
    unittest.main()
