import json
import unittest
from unittest.mock import patch

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

    def test_keeps_a_non_json_cause(self):
        self.assertEqual(
            update_bot_status.error_reason(
                {"Error": "States.Timeout", "Cause": "late"}
            ),
            "late",
        )


if __name__ == "__main__":
    unittest.main()
