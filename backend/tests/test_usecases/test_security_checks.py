import sys
import time
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, ".")

from app import auth
from app.repositories.models.conversation import MessageModel, TextContentModel
from app.usecases import bot as bot_usecase
from app.usecases import chat as chat_usecase
from app.usecases import publication
from app.usecases.chat import trace_to_root, validate_model_is_available
from app.user import User
from jose import JWTError

USER = User(id="user", name="user", email="user@example.com", groups=[])


def message(parent: str | None) -> MessageModel:
    return MessageModel(
        role="user",
        content=[TextContentModel(content_type="text", body="hello")],
        model="claude-v4.7-opus",
        children=[],
        parent=parent,
        create_time=0,
        feedback=None,
        used_chunks=None,
        thinking_log=None,
    )


class TestPublicationPermission(unittest.TestCase):
    def test_shared_bot_publication_requires_edit_permission(self):
        bot = MagicMock()
        bot.is_accessible_by_user.return_value = True
        bot.is_editable_by_user.return_value = False

        with patch.object(publication, "find_bot_by_id", return_value=bot):
            with self.assertRaises(PermissionError):
                publication.fetch_api_key(USER, "bot", "api-key")


class TestTraceToRoot(unittest.TestCase):
    def test_raises_on_cycle(self):
        message_map = {"a": message(parent="b"), "b": message(parent="a")}

        with self.assertRaises(ValueError):
            trace_to_root("a", message_map)


class TestValidateModelIsAvailable(unittest.TestCase):
    def test_rejects_model_outside_global_list(self):
        with patch.object(
            chat_usecase,
            "get_global_available_models",
            return_value=["claude-v4.6-sonnet"],
        ):
            with self.assertRaises(PermissionError):
                validate_model_is_available("claude-v4.7-opus", bot=None)

    def test_rejects_model_inactive_for_bot(self):
        bot = SimpleNamespace(active_models=SimpleNamespace(claude_v4_7_opus=False))
        with patch.object(chat_usecase, "get_global_available_models", return_value=[]):
            with self.assertRaises(PermissionError):
                validate_model_is_available("claude-v4.7-opus", bot=bot)  # type: ignore[arg-type]

    def test_accepts_active_model(self):
        bot = SimpleNamespace(active_models=SimpleNamespace(claude_v4_7_opus=True))
        with patch.object(chat_usecase, "get_global_available_models", return_value=[]):
            validate_model_is_available("claude-v4.7-opus", bot=bot)  # type: ignore[arg-type]


class TestSigningKeys(unittest.TestCase):
    def setUp(self) -> None:
        auth._jwks_cache.update(keys=[], fetched_at=0.0)

    def jwks_response(self, kids: list[str]) -> MagicMock:
        response = MagicMock()
        response.json.return_value = {"keys": [{"kid": kid} for kid in kids]}
        return response

    def test_caches_signing_keys(self):
        with patch.object(
            auth.requests, "get", return_value=self.jwks_response(["k1"])
        ) as get:
            auth._find_signing_key("k1")
            auth._find_signing_key("k1")

        self.assertEqual(get.call_count, 1)

    def test_refreshes_for_unknown_key_at_most_once_a_minute(self):
        auth._jwks_cache.update(keys=[{"kid": "k1"}], fetched_at=time.monotonic() - 120)
        with patch.object(
            auth.requests, "get", return_value=self.jwks_response(["k1"])
        ) as get:
            for _ in range(2):
                with self.assertRaises(JWTError):
                    auth._find_signing_key("unknown")

        self.assertEqual(get.call_count, 1)


class TestVerifyToken(unittest.TestCase):
    def decode(self, claims: dict) -> dict:
        with patch.object(auth, "_find_signing_key"), patch.object(
            auth.jwt, "get_unverified_header", return_value={}
        ), patch.object(auth.jwt, "decode", return_value=claims) as decode:
            result = auth.verify_token("token")
        self.assertEqual(decode.call_args.kwargs["issuer"], auth.ISSUER)
        return result

    def test_accepts_id_tokens(self):
        self.assertEqual(self.decode({"token_use": "id"}), {"token_use": "id"})

    def test_rejects_access_tokens(self):
        with self.assertRaises(JWTError):
            self.decode({"token_use": "access"})


if __name__ == "__main__":
    unittest.main()


class TestChatInputValidation(unittest.TestCase):
    def message(self, **overrides) -> dict:
        return {
            "role": "user",
            "content": [{"content_type": "text", "body": "hi"}],
            "model": "claude-v5.5-haiku",
            "parent_message_id": None,
            **overrides,
        }

    def test_rejects_non_user_roles(self):
        from app.routes.schemas.conversation import MessageInput
        from pydantic import ValidationError

        with self.assertRaises(ValidationError):
            MessageInput.model_validate(self.message(role="assistant"))

    def test_rejects_tool_content(self):
        from app.routes.schemas.conversation import MessageInput
        from pydantic import ValidationError

        tool_use = {
            "content_type": "toolUse",
            "body": {"tool_use_id": "1", "name": "tool", "input": {}},
        }
        with self.assertRaises(ValidationError):
            MessageInput.model_validate(self.message(content=[tool_use]))


class TestPrepareConversation(unittest.TestCase):
    def chat_input(self, bot_id=None, message_id=None):
        from app.routes.schemas.conversation import ChatInput

        return ChatInput.model_validate(
            {
                "conversation_id": "c",
                "message": {
                    "role": "user",
                    "content": [{"content_type": "text", "body": "hi"}],
                    "model": "claude-v5.5-haiku",
                    "parent_message_id": None,
                    "message_id": message_id,
                },
                "bot_id": bot_id,
            }
        )

    def conversation(self, bot_id=None):
        return SimpleNamespace(
            bot_id=bot_id,
            last_message_id="system",
            message_map={"system": message(None)},
        )

    def test_rejects_a_different_bot_for_an_existing_conversation(self):
        with patch.object(
            chat_usecase, "find_conversation_by_id", return_value=self.conversation()
        ):
            with self.assertRaises(ValueError):
                chat_usecase.prepare_conversation(USER, self.chat_input(bot_id="bot"))

    def test_rejects_reserved_message_ids(self):
        for message_id in ("system", "instruction"):
            with patch.object(
                chat_usecase,
                "find_conversation_by_id",
                return_value=self.conversation(),
            ):
                with self.assertRaises(ValueError):
                    chat_usecase.prepare_conversation(
                        USER, self.chat_input(message_id=message_id)
                    )


class TestAdminEditsAnotherUsersBot(unittest.TestCase):
    def test_moves_uploads_into_the_owner_path(self):
        with patch.object(bot_usecase, "move_file_in_s3") as move, patch.object(
            bot_usecase, "delete_file_from_s3"
        ) as delete:
            bot_usecase._update_s3_documents_by_diff(
                "admin", "owner", "bot", ["new.pdf"], ["old.pdf"]
            )

        _, source, destination = move.call_args.args
        self.assertIn("admin/bot", source)
        self.assertIn("owner/bot", destination)
        self.assertIn("owner/bot", delete.call_args.args[1])

    def test_keeps_a_replaced_file_with_the_same_name(self):
        with patch.object(bot_usecase, "move_file_in_s3"), patch.object(
            bot_usecase, "delete_file_from_s3"
        ) as delete:
            bot_usecase._update_s3_documents_by_diff(
                "owner", "owner", "bot", ["deck.pptx.txt"], ["deck.pptx.txt"]
            )

        delete.assert_not_called()
