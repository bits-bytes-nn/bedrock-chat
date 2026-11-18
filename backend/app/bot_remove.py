import logging
import os
from typing import Any

import boto3
from botocore.exceptions import ClientError
from app.repositories.api_publication import delete_published_api
from app.repositories.common import compose_sk, decompose_sk
from app.repositories.conversation import delete_conversation_by_user_id
from app.routes.schemas.bot import SEARCH_API_MAX_RESULTS
from app.user import User
from app.utils import (
    CUSTOM_BOT_STACK_PREFIX,
    compose_upload_document_s3_path,
    delete_api_key_from_secret_manager,
    delete_s3_prefix,
)

DOCUMENT_BUCKET = os.environ.get("DOCUMENT_BUCKET", "bedrock-documents")
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "us-east-1")
# Named per environment by cdk/lib/utils/stack-names.ts.
SHARED_KNOWLEDGE_BASES_STACK_NAME = os.environ.get(
    "SHARED_KNOWLEDGE_BASES_STACK_NAME", ""
)
# The most documents that DeleteKnowledgeBaseDocuments takes at once.
DOCUMENTS_PER_REQUEST = 10
# Statuses of a document that an earlier attempt is already deleting, as in
# embedding_statemachine/bedrock_knowledge_base/synchronize_data_source.py.
DELETING_STATUSES = ("DELETING", "DELETE_IN_PROGRESS")

s3_client = boto3.client("s3", BEDROCK_REGION)

logger = logging.getLogger(__name__)


def delete_custom_bot_stack_by_bot_id(bot_id: str):
    client = boto3.client("cloudformation", BEDROCK_REGION)
    # DeleteStack succeeds when the stack does not exist.
    return client.delete_stack(StackName=f"{CUSTOM_BOT_STACK_PREFIX}{bot_id}")


def delete_from_s3(user_id: str, bot_id: str):
    """Delete all files in S3 bucket for the specified `user_id` and `bot_id`."""
    delete_s3_prefix(s3_client, DOCUMENT_BUCKET, f"{user_id}/{bot_id}/")
    logger.info("Deleted the S3 files of bot %s", bot_id)


def _shared_knowledge_base_data_sources() -> list[tuple[str, str]]:
    """Return the (knowledge base, data source) IDs of the shared knowledge bases."""
    cfn = boto3.client("cloudformation", BEDROCK_REGION)
    try:
        stacks = cfn.describe_stacks(StackName=SHARED_KNOWLEDGE_BASES_STACK_NAME)
    except ClientError as e:
        if "does not exist" in e.response["Error"].get("Message", ""):
            return []
        raise
    outputs = {
        output["OutputKey"]: output["OutputValue"]
        for output in stacks["Stacks"][0].get("Outputs", [])
    }
    # Outputs are KnowledgeBaseId<hash> and DataSource<hash><n>, as read by
    # embedding_statemachine/bedrock_knowledge_base/finalize_shared_knowledge_bases_build.py.
    return [
        (knowledge_base_id, data_source_id)
        for key, knowledge_base_id in outputs.items()
        if key.startswith("KnowledgeBaseId")
        for data_source_key, data_source_id in outputs.items()
        if data_source_key.startswith(
            f"DataSource{key.removeprefix('KnowledgeBaseId')}"
        )
    ]


def delete_shared_knowledge_base_documents(user_id: str, bot_id: str):
    """Delete the bot's documents from the shared knowledge bases.

    The shared knowledge bases stay for other bots, so the documents that the bot
    ingested into them are deleted one by one. Deleting the files alone leaves them
    searchable in the index. The stream image of a deleted bot has no knowledge base
    settings, so every shared data source is listed, also for bots without one.

    Raises:
        RuntimeError: If Bedrock reports a document as failed to delete, so that
            the stream retries the removal.
    """
    if not SHARED_KNOWLEDGE_BASES_STACK_NAME:
        return
    prefix = (
        f"s3://{DOCUMENT_BUCKET}/{compose_upload_document_s3_path(user_id, bot_id, '')}"
    )
    agent = boto3.client("bedrock-agent", BEDROCK_REGION)
    # Every data source is cleaned up before a failure is raised.
    failed: list[str] = []
    for knowledge_base_id, data_source_id in _shared_knowledge_base_data_sources():
        documents = [
            document["identifier"]["s3"]["uri"]
            for page in agent.get_paginator("list_knowledge_base_documents").paginate(
                knowledgeBaseId=knowledge_base_id,
                dataSourceId=data_source_id,
                PaginationConfig={"PageSize": 1000},
            )
            for document in page["documentDetails"]
            if document["identifier"].get("s3", {}).get("uri", "").startswith(prefix)
            # A retried removal finds the documents of the earlier attempt.
            and document.get("status") not in DELETING_STATUSES
        ]
        for i in range(0, len(documents), DOCUMENTS_PER_REQUEST):
            response = agent.delete_knowledge_base_documents(
                knowledgeBaseId=knowledge_base_id,
                dataSourceId=data_source_id,
                documentIdentifiers=[
                    {"dataSourceType": "S3", "s3": {"uri": uri}}
                    for uri in documents[i : i + DOCUMENTS_PER_REQUEST]
                ],
            )
            failed.extend(
                document["identifier"].get("s3", {}).get("uri", "")
                for document in response.get("documentDetails", [])
                if document.get("status") == "FAILED"
            )
        if documents:
            logger.info(
                "Deleted %d documents of bot %s from data source %s",
                len(documents),
                bot_id,
                data_source_id,
            )
    if failed:
        raise RuntimeError(
            f"Failed to delete {len(failed)} documents of bot {bot_id} from the "
            f"shared knowledge bases: {failed[:3]}"
        )


def delete_search_api_keys(user_id: str, bot_id: str):
    """Delete the API key of every search engine, whichever the bot used last."""
    for engine in SEARCH_API_MAX_RESULTS:
        delete_api_key_from_secret_manager(user_id, bot_id, engine)


def handler(event: dict, context: Any) -> None:
    """Bot removal handler, triggered by the DynamoDB stream when a bot is deleted.

    Deletes the knowledge base stack, the published API stack and its API keys, the
    bot's documents in the shared knowledge bases, its S3 files and its search API
    key secrets.
    """

    # NOTE: batch size is 1
    record = event["Records"][0]

    pk = record["dynamodb"]["Keys"]["PK"]["S"]
    sk = record["dynamodb"]["Keys"].get("SK", {}).get("S")
    if not sk or not sk.startswith(compose_sk("", "bot")):
        # Ignore non-bot items
        logger.info("Skipping event for SK: %s", sk)
        return

    user_id = pk
    bot_id = decompose_sk(sk)
    # Also names the bot of a removal that times out (docs/ADMINISTRATOR.md).
    logger.info("Removing bot %s of user %s", bot_id, user_id)

    # Every step runs even if another fails, and the failure is raised at the end so
    # that the stream retries the record. Each step is idempotent. Stacks go first:
    # a leaked knowledge base stack keeps an OpenSearch Serverless collection billing.
    errors: list[Exception] = []
    for step in (
        lambda: delete_custom_bot_stack_by_bot_id(bot_id),
        lambda: delete_published_api(bot_id),
        lambda: delete_shared_knowledge_base_documents(user_id, bot_id),
        lambda: delete_from_s3(user_id, bot_id),
        lambda: delete_search_api_keys(user_id, bot_id),
        # Last, because it can take long: the conversations of the API's clients,
        # stored under the API's own user. A retry continues where it stopped.
        lambda: delete_conversation_by_user_id(User.from_published_api_id(bot_id).id),
    ):
        try:
            step()
        except Exception as e:
            # The keys are logged for a manual retry (docs/ADMINISTRATOR.md).
            logger.exception("Failed to clean up bot %s of user %s", bot_id, user_id)
            errors.append(e)
    if errors:
        raise errors[0]
