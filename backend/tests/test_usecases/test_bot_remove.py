import unittest
from unittest.mock import MagicMock, patch

from app import bot_remove
from app.repositories import api_publication
from app.repositories.common import RecordNotFoundError
from botocore.exceptions import ClientError
from app.repositories.common import ResourceConflictError
from app.usecases import bot as bot_usecase

EVENT = {
    "Records": [
        {"dynamodb": {"Keys": {"PK": {"S": "user"}, "SK": {"S": "user#BOT#bot"}}}}
    ]
}


class TestBotRemoval(unittest.TestCase):
    def test_runs_every_step_and_reports_failures(self):
        with patch.object(
            bot_remove,
            "delete_custom_bot_stack_by_bot_id",
            side_effect=RuntimeError("throttled"),
        ) as delete_kb_stack, patch.object(
            bot_remove, "_delete_published_api"
        ) as delete_api, patch.object(
            bot_remove, "delete_from_s3"
        ) as delete_files, patch.object(
            bot_remove, "delete_api_key_from_secret_manager"
        ) as delete_secret:
            with self.assertRaises(RuntimeError):
                bot_remove.handler(EVENT, None)

        delete_kb_stack.assert_called_once_with("bot")
        delete_api.assert_called_once_with("bot")
        delete_files.assert_called_once_with("user", "bot")
        delete_secret.assert_called_once()

    def test_ignores_items_other_than_bots(self):
        event = {"Records": [{"dynamodb": {"Keys": {"PK": {"S": "user"}}}}]}
        with patch.object(bot_remove, "delete_from_s3") as delete_files:
            bot_remove.handler(event, None)
        delete_files.assert_not_called()


class TestDeleteDuringBuild(unittest.TestCase):
    def bot(self, sync_status: str, build_id: str | None = None) -> MagicMock:
        bot = MagicMock(sync_status=sync_status, published_api_codebuild_id=build_id)
        self.user = MagicMock()
        self.user.is_admin.return_value = False
        bot.is_pinned.return_value = False
        bot.is_editable_by_user.return_value = True
        return bot

    def test_rejects_deleting_while_the_knowledge_base_is_built(self):
        with patch.object(
            bot_usecase, "find_bot_by_id", return_value=self.bot("RUNNING")
        ), patch.object(bot_usecase, "delete_bot_by_id") as delete:
            with self.assertRaises(ResourceConflictError):
                bot_usecase.remove_bot_by_id(self.user, "bot")
        delete.assert_not_called()

    def test_rejects_deleting_while_the_api_is_published(self):
        with patch.object(
            bot_usecase, "find_bot_by_id", return_value=self.bot("SUCCEEDED", "build")
        ), patch.object(
            bot_usecase, "find_build_status_by_build_id", return_value="IN_PROGRESS"
        ), patch.object(
            bot_usecase, "delete_bot_by_id"
        ) as delete:
            with self.assertRaises(ResourceConflictError):
                bot_usecase.remove_bot_by_id(self.user, "bot")
        delete.assert_not_called()

    def test_lets_admins_delete_a_stuck_bot(self):
        bot = self.bot("RUNNING")
        self.user.is_admin.return_value = True
        with patch.object(
            bot_usecase, "find_bot_by_id", return_value=bot
        ), patch.object(bot_usecase, "delete_bot_by_id") as delete:
            bot_usecase.remove_bot_by_id(self.user, "bot")
        delete.assert_called_once()

    def test_allows_deleting_when_the_build_has_expired(self):
        with patch.object(
            bot_usecase, "find_bot_by_id", return_value=self.bot("SUCCEEDED", "old")
        ), patch.object(
            bot_usecase,
            "find_build_status_by_build_id",
            side_effect=bot_usecase.RecordNotFoundError("gone"),
        ), patch.object(
            bot_usecase, "delete_bot_by_id"
        ) as delete:
            bot_usecase.remove_bot_by_id(self.user, "bot")
        delete.assert_called_once()


class TestFindPublishedStack(unittest.TestCase):
    def describe_error(self, message: str) -> ClientError:
        return ClientError(
            {"Error": {"Code": "ValidationError", "Message": message}},
            "DescribeStacks",
        )

    def test_reports_a_missing_stack(self):
        client = MagicMock()
        client.exceptions.ClientError = ClientError
        client.describe_stacks.side_effect = self.describe_error(
            "Stack with id ApiPublishmentStackbot does not exist"
        )
        with patch.object(api_publication.boto3, "client", return_value=client):
            with self.assertRaises(RecordNotFoundError):
                api_publication.find_stack_by_bot_id("bot")

    def test_raises_other_errors(self):
        client = MagicMock()
        client.exceptions.ClientError = ClientError
        client.describe_stacks.side_effect = self.describe_error("Rate exceeded")
        with patch.object(api_publication.boto3, "client", return_value=client):
            with self.assertRaises(ClientError):
                api_publication.find_stack_by_bot_id("bot")


if __name__ == "__main__":
    unittest.main()
