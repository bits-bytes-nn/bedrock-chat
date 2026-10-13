"""The alarms in cdk/lib/constructs/monitoring.ts count log lines by their text."""

import re
import unittest
from pathlib import Path
from unittest.mock import patch

from embedding_statemachine.bedrock_knowledge_base import update_bot_status

REPO = Path(__file__).resolve().parents[2]
MONITORING = REPO / "cdk/lib/constructs/monitoring.ts"


def alarm_terms(metric_id: str) -> list[str]:
    source = MONITORING.read_text()
    match = re.search(rf'loggedErrors\("{metric_id}", [^,]+, \[(.*?)\]\)', source, re.S)
    assert match, metric_id
    return re.findall(r'"([^"]+)"', match.group(1))


class TestAlarmLogTerms(unittest.TestCase):
    def test_chat_error_terms_are_logged_by_the_websocket_handler(self):
        source = (REPO / "backend/app/websocket.py").read_text()
        terms = alarm_terms("ChatErrorCount")
        self.assertTrue(terms)
        for term in terms:
            self.assertIn(f'logger.exception("{term}")', source)

    def test_failed_bot_syncs_are_logged(self):
        (term,) = alarm_terms("BotKnowledgeSyncFailureCount")
        with patch.object(update_bot_status, "update_sync_status"), self.assertLogs(
            update_bot_status.logger, "ERROR"
        ) as logs:
            update_bot_status.handler(
                {"OwnerUserId": "u", "BotId": "b", "SyncStatus": "FAILED"}, None
            )
        self.assertIn(term, logs.output[0])


if __name__ == "__main__":
    unittest.main()
