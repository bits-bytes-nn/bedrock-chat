import unittest
from unittest.mock import MagicMock, patch

import pytest
from app.repositories.conversation import find_conversation_by_id
from app.repositories.models.conversation import (
    MessageModel,
    SimpleMessageModel,
    TextContentModel,
)
from app.routes.schemas.conversation import ChatInput
from app.stream import OnStopInput
from app.prompt import CONTINUE_PROMPT, KNOWLEDGE_BASE_PROMPT
from app.usecases import chat as chat_usecase
from app.user import User

USER = User(id="user", name="user", email="user@example.com", groups=[])
MODEL = "claude-v5.5-haiku"


def answer(
    text: str,
    stop_reason: str = "end_turn",
    model: str = MODEL,
    thinking_log: list[SimpleMessageModel] | None = None,
) -> OnStopInput:
    return {
        "message": MessageModel(
            role="assistant",
            content=[TextContentModel(content_type="text", body=text)] if text else [],
            model=model,
            children=[],
            parent=None,
            create_time=0,
            feedback=None,
            used_chunks=None,
            thinking_log=thinking_log,
        ),
        "stop_reason": stop_reason,
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

    def test_tells_the_model_to_search_the_knowledge_base(self):
        bot = MagicMock(
            id="bot",
            instruction="",
            display_retrieved_chunks=False,
            generation_params=None,
            bedrock_guardrails=None,
        )
        bot.is_agent_enabled.return_value = True
        bot.has_knowledge.return_value = True
        request = chat_input("c3", None, "What is the project code name?")
        request.bot_id = "bot"
        with (
            patch.object(chat_usecase, "fetch_bot", return_value=(True, bot)),
            patch.object(chat_usecase, "validate_model_is_available"),
            patch.object(chat_usecase, "modify_bot_last_used_time"),
            patch.object(chat_usecase, "modify_bot_stats"),
            patch.object(
                chat_usecase, "converse_with_strands", return_value=answer("BLUEFIN-42")
            ) as converse,
        ):
            chat_usecase.chat(USER, request)

        self.assertIn(KNOWLEDGE_BASE_PROMPT, converse.call_args.kwargs["instructions"])

    def test_emits_the_chat_cost_of_every_answer(self):
        # The WebSocket, POST /conversation and SQS handlers all answer through
        # chat(), without emitting the cost themselves.
        with patch.object(chat_usecase, "emit_chat_cost") as emit:
            self.send("c4", None, "hello")
        emit.assert_called_once_with(0.5)

    def test_stored_answer_survives_failed_bot_bookkeeping(self):
        bot = MagicMock(
            id="bot",
            instruction="",
            display_retrieved_chunks=False,
            generation_params=None,
            bedrock_guardrails=None,
        )
        bot.is_agent_enabled.return_value = False
        bot.has_knowledge.return_value = False
        request = chat_input("c5", None, "hello")
        request.bot_id = "bot"
        on_stop = MagicMock()
        with (
            patch.object(chat_usecase, "fetch_bot", return_value=(True, bot)),
            patch.object(chat_usecase, "validate_model_is_available"),
            patch.object(
                chat_usecase,
                "modify_bot_last_used_time",
                side_effect=RuntimeError("throttled"),
            ),
            patch.object(chat_usecase, "modify_bot_stats"),
            patch.object(
                chat_usecase, "converse_with_strands", return_value=answer("hi")
            ),
            self.assertLogs(chat_usecase.logger, "ERROR"),
            patch.object(chat_usecase, "emit_metric") as emit,
        ):
            _, message = chat_usecase.chat(USER, request, on_stop=on_stop)

        emit.assert_called_once_with("BotUsageUpdateFailures", 1)
        on_stop.assert_called_once()
        stored = find_conversation_by_id(USER.id, "c5")
        self.assertEqual(
            stored.message_map[stored.last_message_id].content, message.content
        )

    def cut_off(
        self,
        conversation_id: str,
        model: str = MODEL,
        thinking_log: list[SimpleMessageModel] | None = None,
    ) -> str:
        request = chat_input(conversation_id, None, "write a long essay")
        request.message.model = model
        with patch.object(
            chat_usecase,
            "converse_with_strands",
            return_value=answer("The first half", "max_tokens", model, thinking_log),
        ):
            chat_usecase.chat(USER, request)
        stored = find_conversation_by_id(USER.id, conversation_id)
        self.assertTrue(stored.should_continue)
        return stored.last_message_id

    def continue_answer(
        self,
        conversation_id: str,
        parent: str,
        text: str = ", continued",
        thinking_log: list[SimpleMessageModel] | None = None,
    ):
        request = ChatInput.model_validate(
            {
                "conversation_id": conversation_id,
                "message": {
                    "role": "user",
                    "content": [],
                    # The page may send the model of the conversation's first answer.
                    "model": "claude-v5.5-opus",
                    "parent_message_id": parent,
                },
                "continue_generate": True,
            }
        )
        with patch.object(
            chat_usecase,
            "converse_with_strands",
            return_value=answer(text, thinking_log=thinking_log),
        ) as converse:
            chat_usecase.chat(USER, request)
        return converse.call_args.kwargs

    def joined_answer(self, conversation_id: str) -> MessageModel:
        stored = find_conversation_by_id(USER.id, conversation_id)
        self.assertFalse(stored.should_continue)
        last = stored.message_map[stored.last_message_id]
        self.assertEqual(
            last.content,
            [TextContentModel(content_type="text", body="The first half, continued")],
        )
        # The continuation replaces the cut-off answer instead of adding a turn.
        self.assertEqual(
            stored.message_map[last.parent].children, [stored.last_message_id]
        )
        return last

    def test_continues_without_prefill_by_asking_for_the_rest(self):
        # Claude Haiku 5.5 rejects an assistant prefill.
        answer_id = self.cut_off("c6")
        call = self.continue_answer("c6", answer_id)
        sent = call["messages"]
        self.assertEqual(
            [m.role for m in sent], ["system", "user", "assistant", "user"]
        )
        self.assertEqual(sent[-1].content[0].body, CONTINUE_PROMPT)
        # The model that wrote the answer continues it.
        self.assertEqual(call["chat_input"].message.model, MODEL)
        self.joined_answer("c6")

    def test_continues_with_prefill_from_the_cut_off_answer(self):
        answer_id = self.cut_off("c7", "claude-v4.5-sonnet")
        sent = self.continue_answer("c7", answer_id)["messages"]
        self.assertEqual([m.role for m in sent], ["system", "user", "assistant"])
        self.joined_answer("c7")

    def test_continued_agent_answer_keeps_its_tool_steps(self):
        def step(body: str) -> SimpleMessageModel:
            return SimpleMessageModel(
                role="assistant",
                content=[TextContentModel(content_type="text", body=body)],
            )

        answer_id = self.cut_off("c8", thinking_log=[step("searched")])
        self.continue_answer("c8", answer_id, thinking_log=[step("searched again")])
        last = self.joined_answer("c8")
        self.assertEqual(
            [log.content[0].body for log in last.thinking_log or []],
            ["searched", "searched again"],
        )
        # The answer keeps its id, so its related documents still match.
        self.assertEqual(
            find_conversation_by_id(USER.id, "c8").last_message_id, answer_id
        )

    def test_rejects_continuing_anything_but_the_cut_off_answer(self):
        answer_id = self.cut_off("c9")
        stored = find_conversation_by_id(USER.id, "c9")
        user_msg_id = stored.message_map[answer_id].parent
        for parent in (user_msg_id, "system", "other"):
            with self.subTest(parent=parent), self.assertRaises(ValueError):
                self.continue_answer("c9", parent)

        self.continue_answer("c9", answer_id)
        # A finished answer cannot be continued again.
        with self.assertRaises(ValueError):
            self.continue_answer("c9", answer_id)

    def test_rejects_continuing_a_new_conversation(self):
        with self.assertRaises(ValueError):
            self.continue_answer("c10", "answer")

    def test_answer_without_text_cannot_be_continued(self):
        request = chat_input("c11", None, "think hard")
        with patch.object(
            chat_usecase,
            "converse_with_strands",
            return_value=answer("", "max_tokens"),
        ):
            chat_usecase.chat(USER, request)
        self.assertFalse(find_conversation_by_id(USER.id, "c11").should_continue)


if __name__ == "__main__":
    unittest.main()
