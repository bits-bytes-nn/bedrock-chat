import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, ".")

from app import auth
from app.repositories.models.conversation import MessageModel, TextContentModel
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

    def test_refreshes_once_for_unknown_key(self):
        with patch.object(
            auth.requests, "get", return_value=self.jwks_response(["k1"])
        ) as get:
            with self.assertRaises(JWTError):
                auth._find_signing_key("unknown")

        self.assertEqual(get.call_count, 2)


if __name__ == "__main__":
    unittest.main()
