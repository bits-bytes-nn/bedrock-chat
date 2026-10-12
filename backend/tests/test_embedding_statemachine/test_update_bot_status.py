import json
import unittest
from unittest.mock import patch

import boto3
import pytest
from app.repositories import common

from embedding_statemachine.bedrock_knowledge_base import update_bot_status


class TestFailedSyncReason(unittest.TestCase):
    def test_stores_the_lambda_error_message(self):
        error = {
            "Error": "Exception",
            "Cause": json.dumps(
                {
                    "errorMessage": "1 of 11 document(s) failed.",
                    "errorType": "Exception",
                }
            ),
        }
        with patch.object(update_bot_status, "update_sync_status") as update:
            update_bot_status.handler(
                {
                    "OwnerUserId": "u",
                    "BotId": "b",
                    "SyncStatus": "FAILED",
                    "Error": error,
                },
                None,
            )
        self.assertEqual(
            update.call_args.args[0]["reason"], "1 of 11 document(s) failed."
        )

    def test_keeps_a_build_that_could_not_start(self):
        # StartBuild failures have a plain-text cause.
        cause = "Access denied (Service: CodeBuild)"
        self.assertEqual(
            update_bot_status.error_reason({"Error": "CodeBuild.X", "Cause": cause}),
            (cause, ""),
        )

    def test_stores_the_phases_of_a_failed_build(self):
        build = {"Arn": "arn:build", "Phases": [{"PhaseType": "BUILD"}]}
        reason, last_exec_id = update_bot_status.error_reason(
            {"Error": "States.TaskFailed", "Cause": json.dumps({"Build": build})}
        )
        self.assertEqual(
            (json.loads(reason), last_exec_id), (build["Phases"], "arn:build")
        )


@pytest.mark.usefixtures("dynamodb_tables")
class TestUpdateSyncStatus(unittest.TestCase):
    def test_does_not_recreate_a_deleted_bot(self):
        update_bot_status.update_sync_status(
            {
                "user_id": "user",
                "bot_id": "deleted",
                "status": "FAILED",
                "reason": "",
                "last_exec_id": "",
            }
        )
        table = boto3.resource("dynamodb", region_name=common.REGION).Table(
            common.BOT_TABLE_NAME
        )
        self.assertEqual(table.scan()["Items"], [])


if __name__ == "__main__":
    unittest.main()
