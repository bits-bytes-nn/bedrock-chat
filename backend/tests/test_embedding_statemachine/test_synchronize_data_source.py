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

    def ingest(self, files_diff: dict, statuses: dict[str, str], bucket=None):
        """Ingest one bot's files into a data source holding documents of these statuses."""
        bucket = bucket or synchronize_data_source.DOCUMENT_BUCKET
        with patch.object(synchronize_data_source, "bedrock_agent") as agent:
            agent.get_data_source.return_value = {
                "dataSource": {
                    "dataSourceConfiguration": {
                        "type": "S3",
                        "s3Configuration": {"bucketArn": f"arn:aws:s3:::{bucket}"},
                    }
                }
            }
            agent.get_paginator.return_value.paginate.return_value = [
                {
                    "documentDetails": [
                        {"status": status, "identifier": {"s3": {"uri": document}}}
                        for document, status in statuses.items()
                    ]
                }
            ]
            agent.ingest_knowledge_base_documents.return_value = {"documentDetails": []}
            agent.delete_knowledge_base_documents.return_value = {"documentDetails": []}
            agent.start_ingestion_job.return_value = {
                "ingestionJob": {"ingestionJobId": "job"}
            }
            self.result = synchronize_data_source.handle_ingest(
                {
                    "KnowledgeBaseId": "kb",
                    "DataSourceId": "ds",
                    "FilesDiffs": [
                        {
                            "OwnerUserId": "u",
                            "BotId": "b",
                            "Added": [],
                            "Unchanged": [],
                            "Deleted": [],
                            **files_diff,
                        }
                    ],
                }
            )
        return agent

    @staticmethod
    def uris(call, key: str) -> list[str]:
        if key == "documents":
            return [d["content"]["s3"]["s3Location"]["uri"] for d in call.kwargs[key]]
        return [d["s3"]["uri"] for d in call.kwargs[key]]

    def test_reingests_unchanged_documents_that_failed(self):
        # Retrying a failed sync without changes must not skip the failed files.
        uri = synchronize_data_source.compose_upload_document_s3_uri
        agent = self.ingest(
            {"Unchanged": ["a", "b", "c", "d", "e"]},
            {
                uri("u", "b", "a"): "INDEXED",
                uri("u", "b", "b"): "FAILED",
                uri("u", "b", "d"): "PARTIALLY_INDEXED",
                uri("u", "b", "e"): "IN_PROGRESS",
            },
        )
        self.assertEqual(
            self.uris(agent.ingest_knowledge_base_documents.call_args, "documents"),
            [uri("u", "b", "b"), uri("u", "b", "c"), uri("u", "b", "d")],
        )
        # A document that an earlier sync is still indexing is only checked.
        self.assertEqual(self.result["DocumentsDiff"]["Added"], [uri("u", "b", "e")])

    def test_deletes_the_documents_that_the_bot_no_longer_has(self):
        # A file deleted before a failed sync is in no file list of the retry. The
        # documents of other bots in a shared data source stay.
        uri = synchronize_data_source.compose_upload_document_s3_uri
        agent = self.ingest(
            {"Unchanged": ["kept"]},
            {
                uri("u", "b", "kept"): "INDEXED",
                uri("u", "b", "gone"): "INDEXED",
                uri("u", "b", "going"): "DELETING",
                uri("u", "b2", "other"): "INDEXED",
                uri("u", "b-2", "prefix"): "INDEXED",
            },
        )
        self.assertEqual(
            self.uris(
                agent.delete_knowledge_base_documents.call_args, "documentIdentifiers"
            ),
            [uri("u", "b", "gone")],
        )
        # A document that an earlier sync is still deleting is only checked.
        self.assertEqual(
            self.result["DocumentsDiff"]["Deleted"], [uri("u", "b", "going")]
        )

    def test_synchronizes_a_data_source_of_another_bucket_entirely(self):
        # The data source of an S3 URL of the bot cannot hold the uploaded files.
        agent = self.ingest({"Added": ["new"]}, {}, bucket="other-bucket")
        agent.ingest_knowledge_base_documents.assert_not_called()
        agent.start_ingestion_job.assert_called_once()

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
