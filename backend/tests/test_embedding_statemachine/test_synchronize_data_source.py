import unittest
from unittest.mock import patch

import botocore.session

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


class TestHandleIngest(unittest.TestCase):
    def start(self, execution_id: str) -> dict:
        with patch.object(synchronize_data_source, "bedrock_agent") as agent:
            agent.start_ingestion_job.return_value = {
                "ingestionJob": {"ingestionJobId": "job"}
            }
            synchronize_data_source.handle_ingest(
                {
                    "KnowledgeBaseId": "kb",
                    "DataSourceId": "ds",
                    "FilesDiffs": None,
                    "ExecutionId": execution_id,
                }
            )
        return agent.start_ingestion_job.call_args.kwargs

    def test_reingests_unchanged_documents_that_failed(self):
        # Retrying a failed sync without changes must not skip the failed files.
        statuses = {"a": "INDEXED", "b": "FAILED", "c": "NOT_FOUND"}
        uri = synchronize_data_source.compose_upload_document_s3_uri
        with patch.object(synchronize_data_source, "bedrock_agent") as agent:
            agent.get_data_source.return_value = {
                "dataSource": {"dataSourceConfiguration": {"type": "S3"}}
            }
            agent.get_knowledge_base_documents.return_value = {
                "documentDetails": [
                    {"status": status, "identifier": {"s3": {"uri": uri("u", "b", f)}}}
                    for f, status in statuses.items()
                ]
            }
            agent.ingest_knowledge_base_documents.return_value = {"documentDetails": []}
            synchronize_data_source.handle_ingest(
                {
                    "KnowledgeBaseId": "kb",
                    "DataSourceId": "ds",
                    "FilesDiffs": [
                        {
                            "OwnerUserId": "u",
                            "BotId": "b",
                            "Added": [],
                            "Unchanged": list(statuses),
                            "Deleted": [],
                        }
                    ],
                }
            )
        documents = agent.ingest_knowledge_base_documents.call_args.kwargs["documents"]
        self.assertEqual(
            [d["content"]["s3"]["s3Location"]["uri"] for d in documents],
            [uri("u", "b", "b"), uri("u", "b", "c")],
        )

    def test_retries_of_a_task_reuse_the_job(self):
        first = self.start("arn:execution:1")
        self.assertEqual(
            first["clientToken"], self.start("arn:execution:1")["clientToken"]
        )
        self.assertNotEqual(
            first["clientToken"], self.start("arn:execution:2")["clientToken"]
        )


class TestDocumentsPerRequest(unittest.TestCase):
    def test_matches_the_api_limit(self):
        model = botocore.session.get_session().get_service_model("bedrock-agent")
        for operation, member in (
            ("GetKnowledgeBaseDocuments", "documentIdentifiers"),
            ("IngestKnowledgeBaseDocuments", "documents"),
            ("DeleteKnowledgeBaseDocuments", "documentIdentifiers"),
        ):
            shape = model.operation_model(operation).input_shape.members[member]
            self.assertEqual(
                synchronize_data_source.DOCUMENTS_PER_REQUEST, shape.metadata["max"]
            )
