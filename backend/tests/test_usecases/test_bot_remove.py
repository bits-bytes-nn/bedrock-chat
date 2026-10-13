import json
import unittest
from unittest.mock import MagicMock, call, patch

import pytest
from app import bot_remove, utils
from app.repositories.conversation import find_conversation_by_id, store_conversation
from app.repositories.models.conversation import ConversationModel
from app.usecases import publication
from app.user import User
from app.repositories import api_publication
from app.repositories.common import RecordNotFoundError
from botocore.exceptions import ClientError
from app.repositories.common import ResourceConflictError
from app.usecases import bot as bot_usecase

EVENT = {
    "Records": [{"dynamodb": {"Keys": {"PK": {"S": "user"}, "SK": {"S": "BOT#bot"}}}}]
}


class TestBotRemoval(unittest.TestCase):
    def test_runs_every_step_and_reports_failures(self):
        # One parent records the order of the calls to every step.
        steps = MagicMock()
        steps.delete_custom_bot_stack_by_bot_id.side_effect = RuntimeError("throttled")
        with patch.multiple(
            bot_remove,
            delete_custom_bot_stack_by_bot_id=steps.delete_custom_bot_stack_by_bot_id,
            delete_published_api=steps.delete_published_api,
            delete_from_s3=steps.delete_from_s3,
            delete_api_key_from_secret_manager=steps.delete_api_key_from_secret_manager,
            delete_conversation_by_user_id=steps.delete_conversation_by_user_id,
        ):
            with self.assertRaises(RuntimeError):
                bot_remove.handler(EVENT, None)

        steps.delete_custom_bot_stack_by_bot_id.assert_called_once_with("bot")
        steps.delete_published_api.assert_called_once_with("bot")
        steps.delete_from_s3.assert_called_once_with("user", "bot")
        steps.delete_api_key_from_secret_manager.assert_called_once()
        # The published API's conversations can take long, so they go last.
        self.assertEqual(
            steps.method_calls[-1],
            call.delete_conversation_by_user_id("PUBLISHED_API#bot"),
        )
        self.assertEqual(len(steps.method_calls), 5)

    def test_ignores_items_other_than_bots(self):
        for keys in (
            {"PK": {"S": "user"}},
            {"PK": {"S": "user"}, "SK": {"S": "ALIAS#bot"}},
        ):
            event = {"Records": [{"dynamodb": {"Keys": keys}}]}
            with patch.object(bot_remove, "delete_from_s3") as delete_files:
                bot_remove.handler(event, None)
            delete_files.assert_not_called()


@pytest.mark.usefixtures("dynamodb_tables")
class TestUnpublish(unittest.TestCase):
    def test_keeps_the_published_api_conversations(self):
        user_id = User.from_published_api_id("bot").id
        store_conversation(
            user_id,
            ConversationModel(
                id="c",
                create_time=0,
                title="t",
                total_price=0,
                message_map={},
                last_message_id="",
                bot_id="bot",
                should_continue=False,
            ),
        )
        bot = MagicMock(published_api_codebuild_id="build", owner_user_id="owner")
        with patch.object(
            publication, "find_bot_by_id", return_value=bot
        ), patch.object(
            publication, "is_build_running", return_value=False
        ), patch.object(
            publication, "delete_published_api"
        ) as delete_api, patch.object(
            publication, "delete_bot_publication"
        ):
            publication.remove_bot_publication(MagicMock(), "bot")

        delete_api.assert_called_once_with("bot")
        # Deleted with the bot instead (bot_remove).
        self.assertEqual(find_conversation_by_id(user_id, "c").id, "c")


class TestDeleteDuringBuild(unittest.TestCase):
    def bot(self, sync_status: str, build_id: str | None = None) -> MagicMock:
        bot = MagicMock(
            id="bot", sync_status=sync_status, published_api_codebuild_id=build_id
        )
        self.user = MagicMock()
        self.user.is_admin.return_value = False
        bot.is_pinned.return_value = False
        bot.is_editable_by_user.return_value = True
        return bot

    def test_rejects_deleting_while_the_knowledge_base_is_built(self):
        with patch.object(
            bot_usecase, "find_bot_by_id", return_value=self.bot("RUNNING")
        ), patch.object(
            bot_usecase, "is_embedding_running", return_value=True
        ) as running, patch.object(
            bot_usecase, "delete_bot_by_id"
        ) as delete:
            with self.assertRaises(ResourceConflictError) as e:
                bot_usecase.remove_bot_by_id(self.user, "bot")
        self.assertEqual(e.exception.code, "knowledge_base_syncing")
        running.assert_called_once_with("bot")
        delete.assert_not_called()

    def test_allows_deleting_a_bot_whose_sync_status_is_stuck(self):
        for status in ("QUEUED", "RUNNING"):
            with patch.object(
                bot_usecase, "find_bot_by_id", return_value=self.bot(status)
            ), patch.object(
                bot_usecase, "is_embedding_running", return_value=False
            ), patch.object(
                bot_usecase, "is_build_running", return_value=False
            ), patch.object(
                bot_usecase, "delete_bot_by_id"
            ) as delete:
                bot_usecase.remove_bot_by_id(self.user, "bot")
            delete.assert_called_once()

    def test_rejects_deleting_while_the_api_is_published(self):
        with patch.object(
            bot_usecase, "find_bot_by_id", return_value=self.bot("SUCCEEDED", "build")
        ), patch.object(
            bot_usecase, "is_build_running", return_value=True
        ), patch.object(
            bot_usecase, "delete_bot_by_id"
        ) as delete:
            with self.assertRaises(ResourceConflictError):
                bot_usecase.remove_bot_by_id(self.user, "bot")
        delete.assert_not_called()

    def test_rejects_admins_deleting_during_a_build(self):
        for bot, build_running in (
            (self.bot("RUNNING"), False),
            (self.bot("SUCCEEDED", "build"), True),
        ):
            self.user.is_admin.return_value = True
            with patch.object(
                bot_usecase, "find_bot_by_id", return_value=bot
            ), patch.object(
                bot_usecase, "is_build_running", return_value=build_running
            ), patch.object(
                bot_usecase, "is_embedding_running", return_value=True
            ), patch.object(
                bot_usecase, "delete_bot_by_id"
            ) as delete:
                with self.assertRaises(ResourceConflictError):
                    bot_usecase.remove_bot_by_id(self.user, "bot")
            delete.assert_not_called()

    def test_allows_deleting_when_the_build_has_finished(self):
        with patch.object(
            bot_usecase, "find_bot_by_id", return_value=self.bot("SUCCEEDED", "old")
        ), patch.object(
            bot_usecase, "is_build_running", return_value=False
        ), patch.object(
            bot_usecase, "is_embedding_running"
        ) as running, patch.object(
            bot_usecase, "delete_bot_by_id"
        ) as delete:
            bot_usecase.remove_bot_by_id(self.user, "bot")
        delete.assert_called_once()
        # A finished sync needs no Step Functions calls.
        running.assert_not_called()

    def test_rejects_editing_while_the_knowledge_base_is_built(self):
        for is_admin in (False, True):
            bot = self.bot("QUEUED")
            self.user.is_admin.return_value = is_admin
            with patch.object(
                bot_usecase, "find_bot_by_id", return_value=bot
            ), patch.object(
                bot_usecase, "is_embedding_running", return_value=True
            ), patch.object(
                bot_usecase, "update_bot"
            ) as update:
                with self.assertRaises(ResourceConflictError):
                    bot_usecase.modify_owned_bot(self.user, "bot", MagicMock())
            update.assert_not_called()

    def save_unchanged(
        self,
        current_status: str,
        knowledge_base_type: str = "dedicated",
        files_changed: bool = False,
    ) -> tuple[str, MagicMock]:
        """Save the bot without changing its knowledge base settings.

        Returns the new sync status and the mock of the state machine start.
        """
        bot = self.bot(current_status)
        bot.bedrock_knowledge_base = MagicMock(type=knowledge_base_type)
        modify_input = MagicMock(
            knowledge=None,
            agent=None,
            generation_params=None,
            bedrock_knowledge_base=None,
            bedrock_guardrails=None,
            conversation_quick_starters=None,
        )
        modify_input.is_embedding_required.return_value = files_changed
        modify_input.is_guardrails_update_required.return_value = False
        modify_input.is_sync_shared_knowledge_bases_required.return_value = False
        with patch.multiple(
            bot_usecase,
            find_bot_by_id=MagicMock(return_value=bot),
            validate_external_resource_references=MagicMock(),
            AgentModel=MagicMock(),
            Agent=MagicMock(),
            BotModifyOutput=MagicMock(),
            ActiveModelsOutput=MagicMock(),
            update_bot=MagicMock(),
            start_embedding_state_machine=MagicMock(),
        ):
            bot_usecase.modify_owned_bot(self.user, "bot", modify_input)
            return (
                bot_usecase.update_bot.call_args.kwargs["sync_status"],
                bot_usecase.start_embedding_state_machine,
            )

    def test_saving_retries_a_failed_sync(self):
        status, start = self.save_unchanged("FAILED")
        self.assertEqual(status, "QUEUED")
        start.assert_called_once()
        status, start = self.save_unchanged("SUCCEEDED")
        self.assertEqual(status, "SUCCEEDED")
        start.assert_not_called()

    def test_syncs_an_unchanged_shared_knowledge_base(self):
        # Otherwise the state machine skips the unchanged shared knowledge base.
        for status, files_changed in (("FAILED", False), ("SUCCEEDED", True)):
            _, start = self.save_unchanged(status, "shared", files_changed)
            self.assertTrue(
                start.call_args.kwargs["sync_shared_knowledge_bases_required"]
            )
        _, start = self.save_unchanged("FAILED", "dedicated")
        self.assertFalse(start.call_args.kwargs["sync_shared_knowledge_bases_required"])


class TestIsEmbeddingRunning(unittest.TestCase):
    def running(self, *inputs: dict) -> bool:
        client = MagicMock()
        client.get_paginator.return_value.paginate.return_value = [
            {"executions": [{"executionArn": str(i)} for i in range(len(inputs))]}
        ]
        client.describe_execution.side_effect = lambda executionArn: {
            "input": json.dumps(inputs[int(executionArn)])
        }
        with patch.object(utils.boto3, "client", return_value=client):
            result = utils.is_embedding_running("bot")
        client.get_paginator.return_value.paginate.assert_called_once_with(
            stateMachineArn=utils.EMBEDDING_STATE_MACHINE_ARN, statusFilter="RUNNING"
        )
        return result

    def test_finds_an_execution_for_the_bot(self):
        self.assertTrue(
            self.running(
                {"QueuedBots": [{"BotId": "other"}]},
                {"QueuedBots": [{"BotId": "bot"}]},
            )
        )

    def test_finds_an_execution_for_every_queued_bot(self):
        # Started without input, as in the README, it processes every queued bot.
        self.assertTrue(self.running({}))

    def test_ignores_executions_for_other_bots(self):
        self.assertFalse(self.running({"QueuedBots": [{"BotId": "other"}]}))
        self.assertFalse(self.running())


class TestIsBuildRunning(unittest.TestCase):
    def test_treats_every_terminal_status_as_finished(self):
        for status in ("SUCCEEDED", "FAILED", "FAULT", "STOPPED", "TIMED_OUT"):
            with patch.object(
                api_publication, "find_build_status_by_build_id", return_value=status
            ):
                self.assertFalse(api_publication.is_build_running("b"))

    def test_treats_an_expired_build_as_finished(self):
        with patch.object(
            api_publication,
            "find_build_status_by_build_id",
            side_effect=RecordNotFoundError("gone"),
        ):
            self.assertFalse(api_publication.is_build_running("b"))

    def test_reports_a_running_build(self):
        with patch.object(
            api_publication, "find_build_status_by_build_id", return_value="IN_PROGRESS"
        ):
            self.assertTrue(api_publication.is_build_running("b"))


class TestFindPublishedStack(unittest.TestCase):
    def describe_error(
        self, message: str, code: str = "ValidationError"
    ) -> ClientError:
        return ClientError(
            {"Error": {"Code": code, "Message": message}},
            "DescribeStacks",
        )

    def test_reports_a_missing_stack(self):
        client = MagicMock()
        client.exceptions.ClientError = ClientError
        client.describe_stacks.side_effect = self.describe_error(
            "Stack with id ApiPublishmentStackbot does not exist"
        )
        with patch.object(api_publication.boto3, "client", return_value=client):
            with self.assertRaises(RecordNotFoundError) as e:
                api_publication.find_stack_by_bot_id("bot")
        self.assertEqual(e.exception.code, "bot_not_published")
        self.assertIn("bot", str(e.exception))

    def test_raises_other_errors(self):
        client = MagicMock()
        client.exceptions.ClientError = ClientError
        client.describe_stacks.side_effect = self.describe_error("Rate exceeded")
        with patch.object(api_publication.boto3, "client", return_value=client):
            with self.assertRaises(ClientError):
                api_publication.find_stack_by_bot_id("bot")

    def test_does_not_trust_the_message_alone(self):
        client = MagicMock()
        client.exceptions.ClientError = ClientError
        client.describe_stacks.side_effect = self.describe_error(
            "Role does not exist", code="AccessDenied"
        )
        with patch.object(api_publication.boto3, "client", return_value=client):
            with self.assertRaises(ClientError):
                api_publication.find_stack_by_bot_id("bot")


if __name__ == "__main__":
    unittest.main()
