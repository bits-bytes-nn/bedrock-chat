import hashlib
import os
from itertools import islice
from typing import TypedDict

from app.utils import (
    compose_upload_document_s3_path,
    get_bedrock_agent_client,
)

DOCUMENT_BUCKET = os.environ.get("DOCUMENT_BUCKET")
# The most documents that the Get, Ingest and Delete KnowledgeBaseDocuments APIs
# accept in one request.
DOCUMENTS_PER_REQUEST = 10
bedrock_agent = get_bedrock_agent_client()


def handler(event, context):
    """Perform data source synchronization for a Knowledge Base."""
    match event["Action"]:
        case "Ingest":
            return handle_ingest(event)

        case "Check":
            return handle_check(event)

        case _ as e:
            raise Exception(f"Unknown action {e}")


class DocumentsDiff(TypedDict):
    Added: list[str]
    Deleted: list[str]


def compose_upload_document_s3_uri(user_id: str, bot_id: str, filename: str) -> str:
    return f"s3://{DOCUMENT_BUCKET}/{compose_upload_document_s3_path(user_id, bot_id, filename)}"


# Statuses of a document that a sync must ingest again.
REINGEST_STATUSES = (
    "NOT_FOUND",
    "FAILED",
    "PARTIALLY_INDEXED",
    "METADATA_UPDATE_FAILED",
    "METADATA_PARTIALLY_INDEXED",
)
# Statuses of a document that an earlier sync is still indexing or deleting.
INDEXING_STATUSES = ("PENDING", "STARTING", "IN_PROGRESS")
DELETING_STATUSES = ("DELETING", "DELETE_IN_PROGRESS")


def reads_document_bucket(knowledge_base_id: str, data_source_id: str) -> bool:
    """Whether the data source reads the bucket of the files uploaded to bots."""
    data_source = bedrock_agent.get_data_source(
        knowledgeBaseId=knowledge_base_id,
        dataSourceId=data_source_id,
    )["dataSource"]
    s3_configuration = data_source["dataSourceConfiguration"].get("s3Configuration", {})
    return s3_configuration.get("bucketArn", "").endswith(f":::{DOCUMENT_BUCKET}")


def list_document_statuses(
    knowledge_base_id: str, data_source_id: str
) -> dict[str, str]:
    """Return the status of each S3 document in the data source by its URI."""
    paginator = bedrock_agent.get_paginator("list_knowledge_base_documents")
    return {
        document["identifier"]["s3"]["uri"]: document["status"]
        for page in paginator.paginate(
            knowledgeBaseId=knowledge_base_id,
            dataSourceId=data_source_id,
            PaginationConfig={"PageSize": 1000},
        )
        for document in page["documentDetails"]
        if "s3" in document["identifier"]
    }


def handle_ingest(event):
    """Perform data source synchronization for Knowledge Bases.

    This function handles both shared and dedicated Knowledge Base DataSources.
    The target DataSource is determined by KnowledgeBaseId/DataSourceId in the event,
    regardless of whether called from SharedKnowledgeBases flow or MapQueuedBots flow.

    Shared KB bots with file diffs reach here via MapQueuedBots flow but still
    update the shared Knowledge Base's DataSources with bot-specific file changes.
    """
    knowledge_base_id = event["KnowledgeBaseId"]
    data_source_id = event["DataSourceId"]

    bot_files_diffs = event.get("FilesDiffs")
    if bot_files_diffs and reads_document_bucket(
        knowledge_base_id=knowledge_base_id,
        data_source_id=data_source_id,
    ):
        # If the bot specifies which files should be ingested, perform direct ingestion.
        statuses = list_document_statuses(knowledge_base_id, data_source_id)
        added_documents: list[str] = []
        deleted_documents: list[str] = []
        # The Check action also waits for the documents of an earlier sync.
        documents_diff: DocumentsDiff = {
            "Added": [],
            "Deleted": [],
        }

        for bot_files_diff in bot_files_diffs:
            user_id = bot_files_diff["OwnerUserId"]
            bot_id = bot_files_diff["BotId"]
            files = [*bot_files_diff["Added"], *bot_files_diff["Unchanged"]]
            bot_documents = {
                compose_upload_document_s3_uri(user_id, bot_id, file) for file in files
            }

            added_documents.extend(
                compose_upload_document_s3_uri(user_id, bot_id, added_file)
                for added_file in bot_files_diff["Added"]
            )
            for unchanged_file in bot_files_diff["Unchanged"]:
                document = compose_upload_document_s3_uri(
                    user_id, bot_id, unchanged_file
                )
                status = statuses.get(document, "NOT_FOUND")
                # If an 'unchanged' document doesn't actually exist or failed in an
                # earlier sync, treat it as an 'added' document.
                if status in REINGEST_STATUSES:
                    added_documents.append(document)
                elif status in INDEXING_STATUSES:
                    documents_diff["Added"].append(document)
            # Delete every document of the bot that it no longer has, not only the
            # 'deleted' files of this save: the files deleted before a failed sync
            # are still in the data source.
            bot_prefix = compose_upload_document_s3_uri(user_id, bot_id, "")
            for document, status in statuses.items():
                if document.startswith(bot_prefix) and document not in bot_documents:
                    if status in DELETING_STATUSES:
                        documents_diff["Deleted"].append(document)
                    else:
                        deleted_documents.append(document)

        # Ingest 'added' documents to the data source.
        for i in range(0, len(added_documents), DOCUMENTS_PER_REQUEST):
            ingest_response = bedrock_agent.ingest_knowledge_base_documents(
                knowledgeBaseId=knowledge_base_id,
                dataSourceId=data_source_id,
                documents=[
                    {
                        "content": {
                            "dataSourceType": "S3",
                            "s3": {
                                "s3Location": {
                                    "uri": document_identifier,
                                },
                            },
                        },
                    }
                    for document_identifier in islice(
                        added_documents, i, i + DOCUMENTS_PER_REQUEST
                    )
                ],
            )
            documents_diff["Added"].extend(
                document["identifier"]["s3"]["uri"]
                for document in ingest_response["documentDetails"]
                if document["status"] != "IGNORED" and "s3" in document["identifier"]
            )

        # Delete 'deleted' documents from the data source.
        for i in range(0, len(deleted_documents), DOCUMENTS_PER_REQUEST):
            delete_response = bedrock_agent.delete_knowledge_base_documents(
                knowledgeBaseId=knowledge_base_id,
                dataSourceId=data_source_id,
                documentIdentifiers=[
                    {
                        "dataSourceType": "S3",
                        "s3": {
                            "uri": document_identifier,
                        },
                    }
                    for document_identifier in islice(
                        deleted_documents, i, i + DOCUMENTS_PER_REQUEST
                    )
                ],
            )
            documents_diff["Deleted"].extend(
                document["identifier"]["s3"]["uri"]
                for document in delete_response["documentDetails"]
                if "s3" in document["identifier"]
            )

        return {
            "KnowledgeBaseId": knowledge_base_id,
            "DataSourceId": data_source_id,
            "DocumentsDiff": documents_diff,
            "IngestionJobId": None,
        }

    else:
        # Otherwise, start the entire synchronization job.
        # Without a token, a retry of this task fails with a ConflictException
        # because the job it started is still running.
        token = {}
        if event.get("ExecutionId"):
            seed = f"{event['ExecutionId']}:{knowledge_base_id}:{data_source_id}"
            token["clientToken"] = hashlib.sha256(seed.encode()).hexdigest()
        start_job_response = bedrock_agent.start_ingestion_job(
            knowledgeBaseId=knowledge_base_id,
            dataSourceId=data_source_id,
            **token,
        )
        ingestion_job_id = start_job_response["ingestionJob"]["ingestionJobId"]

        return {
            "KnowledgeBaseId": knowledge_base_id,
            "DataSourceId": data_source_id,
            "DocumentsDiff": None,
            "IngestionJobId": ingestion_job_id,
        }


class RetryException(Exception):
    pass


def handle_check(event):
    """Check for the completion of direct ingestion or entire synchronization."""
    ingestion_job = event["IngestionJob"]
    knowledge_base_id = ingestion_job["KnowledgeBaseId"]
    data_source_id = ingestion_job["DataSourceId"]

    documents_diff = ingestion_job.get("DocumentsDiff")
    if documents_diff:
        # Check for the completion of indexing of 'added' documents.
        added_documents = documents_diff["Added"]
        for i in range(0, len(added_documents), DOCUMENTS_PER_REQUEST):
            get_documents_response = bedrock_agent.get_knowledge_base_documents(
                knowledgeBaseId=knowledge_base_id,
                dataSourceId=data_source_id,
                documentIdentifiers=[
                    {
                        "dataSourceType": "S3",
                        "s3": {
                            "uri": document_identifier,
                        },
                    }
                    for document_identifier in islice(
                        added_documents, i, i + DOCUMENTS_PER_REQUEST
                    )
                ],
            )
            for document in get_documents_response["documentDetails"]:
                status = document["status"]
                uri = document["identifier"].get("s3", {})["uri"]
                match status:
                    case "INDEXED":
                        pass

                    case _ if status in INDEXING_STATUSES:
                        raise RetryException()

                    case _:
                        raise Exception(f"File {uri}: Bad status '{status}'.")

        # Check for the absence of 'deleted' documents.
        deleted_documents = documents_diff["Deleted"]
        for i in range(0, len(deleted_documents), DOCUMENTS_PER_REQUEST):
            get_documents_response = bedrock_agent.get_knowledge_base_documents(
                knowledgeBaseId=knowledge_base_id,
                dataSourceId=data_source_id,
                documentIdentifiers=[
                    {
                        "dataSourceType": "S3",
                        "s3": {
                            "uri": document_identifier,
                        },
                    }
                    for document_identifier in islice(
                        deleted_documents, i, i + DOCUMENTS_PER_REQUEST
                    )
                ],
            )
            for document in get_documents_response["documentDetails"]:
                status = document["status"]
                uri = document["identifier"].get("s3", {})["uri"]
                match status:
                    case "NOT_FOUND":
                        pass

                    case _ if status == "PENDING" or status in DELETING_STATUSES:
                        raise RetryException()

                    case _:
                        raise Exception(f"File '{uri}': Bad status '{status}'.")

        return

    else:
        # Check the completion of entire synchronization job.
        ingestion_job_id = ingestion_job.get("IngestionJobId")
        if ingestion_job_id:
            get_job_response = bedrock_agent.get_ingestion_job(
                knowledgeBaseId=knowledge_base_id,
                dataSourceId=data_source_id,
                ingestionJobId=ingestion_job_id,
            )
            job = get_job_response["ingestionJob"]
            status = job["status"]
            match status:
                case "COMPLETE":
                    # A job completes even when documents failed to ingest. Report
                    # any failure: a failed upload would otherwise look searchable.
                    statistics = job.get("statistics", {})
                    failed = statistics.get("numberOfDocumentsFailed", 0)
                    if failed:
                        scanned = statistics.get("numberOfDocumentsScanned", 0)
                        reasons = "; ".join(job.get("failureReasons", [])[:3])
                        raise Exception(
                            f"Ingestion Job '{ingestion_job_id}': {failed} of {scanned} document(s) failed. {reasons}"
                        )

                case "STARTING" | "IN_PROGRESS":
                    raise RetryException()

                case _:
                    raise Exception(
                        f"Ingestion Job '{ingestion_job_id}': Bad status '{status}'."
                    )

            return

    raise Exception("Invalid parameters.")
