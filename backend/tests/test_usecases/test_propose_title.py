import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, ".")

from app.repositories.models.conversation import (
    ReasoningContentModel,
    SimpleMessageModel,
    TextContentModel,
)
from app.usecases import chat as chat_usecase


def text(body: str) -> TextContentModel:
    return TextContentModel(content_type="text", body=body)


class TestProposeConversationTitle(unittest.TestCase):
    def propose(self, messages: list[SimpleMessageModel]) -> dict:
        conversation = SimpleNamespace(last_message_id="last", message_map={})
        response = {"output": {"message": {"content": [{"text": "Title"}]}}}
        with (
            patch.object(
                chat_usecase, "find_conversation_by_id", return_value=conversation
            ),
            patch.object(chat_usecase, "trace_to_root", return_value=messages),
            patch.object(chat_usecase, "get_model_id", return_value="model-id"),
            patch.object(
                chat_usecase, "call_converse_api", return_value=response
            ) as call,
        ):
            self.assertEqual(
                chat_usecase.propose_conversation_title("user", "c"), "Title"
            )
        return call.call_args.args[0]

    def test_keeps_answer_text_and_drops_reasoning(self):
        args = self.propose(
            [
                SimpleMessageModel(role="system", content=[text("")]),
                SimpleMessageModel(role="user", content=[text("What is 17 x 23?")]),
                SimpleMessageModel(
                    role="assistant",
                    content=[
                        ReasoningContentModel(
                            content_type="reasoning",
                            text="Multiply.",
                            signature="sig",
                            redacted_content=b"",
                        ),
                        text("391"),
                    ],
                ),
            ]
        )

        roles = [message["role"] for message in args["messages"]]
        self.assertEqual(roles, ["user", "assistant", "user"])
        self.assertEqual(args["messages"][1]["content"], [{"text": "391"}])
        self.assertEqual(args["modelId"], "model-id")

    def test_merges_consecutive_messages_of_the_same_role(self):
        args = self.propose(
            [
                SimpleMessageModel(role="user", content=[text("First")]),
                SimpleMessageModel(role="user", content=[text("Second")]),
            ]
        )

        self.assertEqual([m["role"] for m in args["messages"]], ["user"])
        self.assertTrue(
            args["messages"][0]["content"][0]["text"].startswith("First\nSecond")
        )


if __name__ == "__main__":
    unittest.main()
