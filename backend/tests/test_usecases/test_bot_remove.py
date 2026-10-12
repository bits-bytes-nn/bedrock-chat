import unittest
from unittest.mock import MagicMock, patch

from app import bot_remove
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
        bot.is_pinned.return_value = False
        bot.is_editable_by_user.return_value = True
        return bot

    def test_rejects_deleting_while_the_knowledge_base_is_built(self):
        with patch.object(
            bot_usecase, "find_bot_by_id", return_value=self.bot("RUNNING")
        ), patch.object(bot_usecase, "delete_bot_by_id") as delete:
            with self.assertRaises(ResourceConflictError):
                bot_usecase.remove_bot_by_id(MagicMock(), "bot")
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
                bot_usecase.remove_bot_by_id(MagicMock(), "bot")
        delete.assert_not_called()


if __name__ == "__main__":
    unittest.main()
