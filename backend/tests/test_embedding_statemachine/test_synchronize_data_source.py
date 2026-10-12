import unittest
from unittest.mock import patch

from embedding_statemachine.bedrock_knowledge_base import synchronize_data_source

EVENT = {
    "IngestionJob": {
        "KnowledgeBaseId": "kb",
        "DataSourceId": "ds",
        "IngestionJobId": "job",
    }
}


def job(status: str, failed: int = 0, scanned: int = 1) -> dict:
    return {
        "ingestionJob": {
            "status": status,
            "statistics": {
                "numberOfDocumentsFailed": failed,
                "numberOfDocumentsScanned": scanned,
            },
            "failureReasons": ["Parsing failed for handbook.pdf"] if failed else [],
        }
    }


class TestHandleCheck(unittest.TestCase):
    def check(self, response: dict):
        with patch.object(synchronize_data_source, "bedrock_agent") as agent:
            agent.get_ingestion_job.return_value = response
            return synchronize_data_source.handle_check(EVENT)

    def test_completes_when_every_document_is_ingested(self):
        self.assertIsNone(self.check(job("COMPLETE")))

    def test_fails_when_any_document_fails(self):
        # A new upload that fails among indexed documents must not look searchable.
        with self.assertRaisesRegex(
            Exception, "1 of 11 document\\(s\\) failed. Parsing"
        ):
            self.check(job("COMPLETE", failed=1, scanned=11))

    def test_retries_while_running(self):
        with self.assertRaises(synchronize_data_source.RetryException):
            self.check(job("IN_PROGRESS"))


if __name__ == "__main__":
    unittest.main()
