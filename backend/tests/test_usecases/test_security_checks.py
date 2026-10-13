import json
import sys
import time
import unittest
from types import SimpleNamespace
from typing import get_args
from unittest.mock import MagicMock, patch

sys.path.insert(0, ".")

from app import auth
from app.repositories.models.conversation import MessageModel, TextContentModel
from app.repositories.common import RecordNotFoundError
from app.repositories.models.custom_bot import ActiveModelsModel
from app.routes.schemas.api_publication import (
    BotPublishInput,
    PublishedApiQuota,
    PublishedApiThrottle,
)
from app.routes.schemas.conversation import active_model_field_name, type_model_name
from app.usecases import bot as bot_usecase
from app.usecases import chat as chat_usecase
from app.usecases import publication
from app.usecases.chat import trace_to_root, validate_model_is_available
from app.user import User
import jwt as pyjwt
from jwt import PyJWTError as JWTError

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


class TestPublication(unittest.TestCase):
    def test_unpublished_bot_is_reported_with_a_code(self):
        bot = MagicMock(published_api_codebuild_id=None)
        with patch.object(publication, "find_bot_by_id", return_value=bot):
            for call in (
                publication.fetch_bot_publication,
                publication.remove_bot_publication,
            ):
                with self.assertRaises(RecordNotFoundError) as e:
                    call(USER, "bot")
                self.assertEqual(e.exception.code, "bot_not_published")

    def test_passes_allowed_origins_as_json(self):
        origins = ["https://a.example.com", "https://b.example.com:8443"]
        bot = MagicMock(shared_scope="all", published_api_codebuild_id=None)
        with (
            patch.object(publication, "find_bot_by_id", return_value=bot),
            patch.object(publication, "start_codebuild_project") as start,
            patch.object(publication, "update_bot_publication"),
        ):
            publication.create_bot_publication(
                USER,
                "bot",
                BotPublishInput(
                    stage="api",
                    quota=PublishedApiQuota(limit=None, offset=None, period=None),
                    throttle=PublishedApiThrottle(rate_limit=None, burst_limit=None),
                    allowed_origins=origins,
                ),
            )
        env = start.call_args.kwargs["environment_variables"]
        self.assertEqual(json.loads(env["PUBLISHED_API_ALLOWED_ORIGINS"]), origins)


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

    def test_rejects_model_without_a_field(self):
        bot = SimpleNamespace(active_models=SimpleNamespace())
        with patch.object(chat_usecase, "get_global_available_models", return_value=[]):
            with self.assertRaises(PermissionError):
                validate_model_is_available("claude-v4.7-opus", bot=bot)  # type: ignore[arg-type]

    def test_every_model_has_an_active_models_field(self):
        fields = ActiveModelsModel.model_fields
        for model in get_args(type_model_name):
            self.assertIn(active_model_field_name(model), fields)

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
    """Signs real tokens with a test key served as the user pool JWKS."""

    @classmethod
    def setUpClass(cls):
        from cryptography.hazmat.primitives.asymmetric import rsa

        cls.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        jwk = json.loads(
            pyjwt.algorithms.RSAAlgorithm.to_jwk(cls.private_key.public_key())
        )
        cls.jwks = [{**jwk, "kid": "k1", "alg": "RS256", "use": "sig"}]

    def token(self, **claims) -> str:
        payload = {
            "sub": "user",
            "aud": "client",
            "iss": auth.ISSUER,
            "exp": int(time.time()) + 300,
            "token_use": "id",
            **claims,
        }
        return pyjwt.encode(
            payload, self.private_key, algorithm="RS256", headers={"kid": "k1"}
        )

    def verify(self, token: str) -> dict:
        with (
            patch.object(auth, "_get_signing_keys", return_value=self.jwks),
            patch.object(auth, "CLIENT_ID", "client"),
        ):
            return auth.verify_token(token)

    def test_accepts_id_tokens(self):
        self.assertEqual(self.verify(self.token())["sub"], "user")

    def test_tolerates_small_clock_skew(self):
        issued = int(time.time()) + 2
        self.assertEqual(self.verify(self.token(iat=issued))["sub"], "user")

    def test_rejects_access_tokens(self):
        with self.assertRaises(JWTError):
            self.verify(self.token(token_use="access"))

    def test_rejects_other_issuers_audiences_and_expired_tokens(self):
        for claims in (
            {"iss": "https://example.com"},
            {"aud": "other-client"},
            {"exp": int(time.time()) - 60},
        ):
            with self.assertRaises(JWTError):
                self.verify(self.token(**claims))

    def test_rejects_unsigned_tokens(self):
        unsigned = pyjwt.encode(
            {"sub": "user", "token_use": "id"},
            key=None,
            algorithm="none",
            headers={"kid": "k1"},
        )
        with self.assertRaises(JWTError):
            self.verify(unsigned)


class TestPartialSharing(unittest.TestCase):
    bot = SimpleNamespace(
        owner_user_id="owner",
        shared_scope="partial",
        allowed_cognito_users=[],
        allowed_cognito_groups=["team"],
    )

    def accessible(self, user: User) -> bool:
        from app.repositories.models.custom_bot import BotModel

        return BotModel.is_accessible_by_user(self.bot, user)  # type: ignore[arg-type]

    def test_uses_the_groups_in_the_token(self):
        member = User(id="m", name="m", email="m@example.com", groups=["team"])
        self.assertTrue(self.accessible(member))

    def test_ignores_the_email_claim(self):
        # A user who set another member's email is not a member.
        other = User(id="o", name="o", email="m@example.com", groups=[])
        self.assertFalse(self.accessible(other))


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
        with (
            patch.object(bot_usecase, "move_file_in_s3") as move,
            patch.object(bot_usecase, "delete_file_from_s3") as delete,
        ):
            bot_usecase._update_s3_documents_by_diff(
                "admin", "owner", "bot", ["new.pdf"], ["old.pdf"]
            )

        _, source, destination = move.call_args.args
        self.assertIn("admin/bot", source)
        self.assertIn("owner/bot", destination)
        self.assertIn("owner/bot", delete.call_args.args[1])

    def test_keeps_a_replaced_file_with_the_same_name(self):
        with (
            patch.object(bot_usecase, "move_file_in_s3"),
            patch.object(bot_usecase, "delete_file_from_s3") as delete,
        ):
            bot_usecase._update_s3_documents_by_diff(
                "owner", "owner", "bot", ["deck.pptx.txt"], ["deck.pptx.txt"]
            )

        delete.assert_not_called()
