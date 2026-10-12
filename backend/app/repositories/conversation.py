import json
import logging
import os
from decimal import Decimal as decimal
from typing import Any

import boto3
from app.repositories.common import (
    TRANSACTION_BATCH_WRITE_SIZE,
    RecordNotFoundError,
    ResourceConflictError,
    compose_conv_id,
    compose_related_document_source_id,
    decompose_conv_id,
    decompose_related_document_source_id,
    get_conversation_table_client,
)
from app.repositories.models.conversation import (
    ConversationMeta,
    ConversationModel,
    FeedbackModel,
    MessageModel,
    RelatedDocumentModel,
    ToolResultModel,
    merge_conversations,
)
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from pydantic import TypeAdapter
from ulid import ULID

logger = logging.getLogger(__name__)

THRESHOLD_LARGE_MESSAGE = 300 * 1024  # 300KB
LARGE_MESSAGE_BUCKET = os.environ.get("LARGE_MESSAGE_BUCKET")

BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "us-east-1")
s3_client = boto3.client("s3", BEDROCK_REGION)


# Concurrent writes to one conversation are rare, so a few merges are enough.
MAX_STORE_ATTEMPTS = 3


def _large_message_path(user_id: str, conversation_id: str) -> str:
    # Unique per write, so that concurrent writers never share an object.
    return f"{user_id}/{conversation_id}/message_map-{ULID()}.json"


def _delete_large_messages(user_id: str, conversation_id: str):
    """Delete every stored version of a large message map."""
    paginator = s3_client.get_paginator("list_objects_v2")
    for page in paginator.paginate(
        Bucket=LARGE_MESSAGE_BUCKET, Prefix=f"{user_id}/{conversation_id}/"
    ):
        keys = [{"Key": obj["Key"]} for obj in page.get("Contents", [])]
        if keys:
            s3_client.delete_objects(
                Bucket=LARGE_MESSAGE_BUCKET, Delete={"Objects": keys}
            )


def _put_conversation(user_id: str, conversation: ConversationModel, threshold: int):
    """Write the conversation if nobody else wrote it since it was read.

    Raises:
        ResourceConflictError: If the stored version changed.
    """
    table = get_conversation_table_client(user_id)
    version = conversation.version + 1

    item_params = {
        "PK": user_id,
        "SK": compose_conv_id(user_id, conversation.id),
        "Title": conversation.title,
        "CreateTime": decimal(conversation.create_time),
        # Convert to decimal via str to avoid error
        # Ref: https://stackoverflow.com/questions/63026648/errormessage-class-decimal-inexact-class-decimal-rounded-while
        "TotalPrice": decimal(str(conversation.total_price)),
        "LastMessageId": conversation.last_message_id,
        "ShouldContinue": conversation.should_continue,
        "Version": version,
    }

    if conversation.bot_id:
        item_params["BotId"] = conversation.bot_id

    message_map = {
        k: v.model_dump(by_alias=True) for k, v in conversation.message_map.items()
    }
    message_map_size = len(json.dumps(message_map).encode("utf-8"))
    logger.info(f"Message map size: {message_map_size}")
    large_message_path = None
    if message_map_size > threshold:
        logger.info(
            f"Message map size {message_map_size} exceeds threshold {threshold}"
        )
        item_params["IsLargeMessage"] = True
        # Each write has its own object, so a write that loses the race does not
        # overwrite the stored messages.
        large_message_path = _large_message_path(user_id, conversation.id)
        item_params["LargeMessagePath"] = large_message_path
        s3_client.put_object(
            Bucket=LARGE_MESSAGE_BUCKET,
            Key=large_message_path,
            Body=json.dumps(message_map),
        )
        # Store only `system` attribute in DynamoDB
        item_params["MessageMap"] = json.dumps(
            {k: v for k, v in message_map.items() if k == "system"}
        )
    else:
        item_params["IsLargeMessage"] = False
        item_params["MessageMap"] = json.dumps(message_map)

    # Items written before versioning have no Version attribute.
    condition: dict[str, Any] = (
        {"ConditionExpression": "attribute_not_exists(Version)"}
        if conversation.version == 0
        else {
            "ConditionExpression": "Version = :version",
            "ExpressionAttributeValues": {":version": conversation.version},
        }
    )
    try:
        previous = table.put_item(
            Item=item_params, ReturnValues="ALL_OLD", **condition
        ).get("Attributes", {})
    except ClientError as e:
        if large_message_path:
            s3_client.delete_object(Bucket=LARGE_MESSAGE_BUCKET, Key=large_message_path)
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise ResourceConflictError(
                f"Conversation {conversation.id} was updated concurrently."
            ) from e
        raise

    previous_path = previous.get("LargeMessagePath")
    if previous_path and previous_path != large_message_path:
        # Readers that loaded the previous item retry once (see find_conversation_by_id).
        s3_client.delete_object(Bucket=LARGE_MESSAGE_BUCKET, Key=previous_path)
    conversation.version = version
    conversation.mark_stored()


def store_conversation(
    user_id: str, conversation: ConversationModel, threshold=THRESHOLD_LARGE_MESSAGE
):
    """Store the conversation, merging it with concurrent writes.

    On a conflict, the changes made to this copy since it was read are applied to
    the latest stored conversation. The merged result is written back into
    `conversation`.

    Raises:
        ResourceConflictError: If the conversation keeps changing concurrently.
    """
    logger.info("Storing conversation: %s", conversation.id)
    for attempt in range(MAX_STORE_ATTEMPTS):
        try:
            _put_conversation(user_id, conversation, threshold)
            return
        except ResourceConflictError:
            if attempt == MAX_STORE_ATTEMPTS - 1:
                raise
            logger.warning(
                "Conversation %s changed concurrently. Merging.", conversation.id
            )
            latest = find_conversation_by_id(user_id, conversation.id)
            merged = merge_conversations(conversation._stored, conversation, latest)
            for field in ConversationModel.model_fields:
                setattr(conversation, field, getattr(merged, field))
            conversation._stored = latest._stored


def find_conversation_by_user_id(user_id: str) -> list[ConversationMeta]:
    logger.info(f"Finding conversations for user: {user_id}")
    table = get_conversation_table_client(user_id)

    query_params = {
        "KeyConditionExpression": Key("PK").eq(user_id)
        # NOTE: Need SK to fetch only conversations
        & Key("SK").begins_with(f"{user_id}#CONV#"),
        "ScanIndexForward": False,
    }

    response = table.query(**query_params)
    conversations = [
        ConversationMeta(
            id=decompose_conv_id(item["SK"]),
            create_time=float(item["CreateTime"]),
            title=item["Title"],
            # NOTE: all message has the same model
            model=json.loads(item["MessageMap"]).get("system", {}).get("model", ""),
            bot_id=item["BotId"] if "BotId" in item else None,
        )
        for item in response["Items"]
    ]

    query_count = 1
    MAX_QUERY_COUNT = 5
    while "LastEvaluatedKey" in response:
        model = (
            json.loads(response["Items"][0]["MessageMap"])
            .get("system", {})
            .get("model", "")
        )
        query_params["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        # NOTE: max page size is 1MB
        # See: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Query.Pagination.html
        response = table.query(
            **query_params,
        )
        conversations.extend(
            [
                ConversationMeta(
                    id=decompose_conv_id(item["SK"]),
                    create_time=float(item["CreateTime"]),
                    title=item["Title"],
                    model=model,
                    bot_id=item["BotId"] if "BotId" in item else None,
                )
                for item in response["Items"]
            ]
        )
        query_count += 1
        if query_count > MAX_QUERY_COUNT:
            logger.warning(f"Query count exceeded {MAX_QUERY_COUNT}")
            break

    logger.info("Found %d conversations", len(conversations))
    return conversations


def find_conversation_by_id(user_id: str, conversation_id: str) -> ConversationModel:
    logger.info(f"Finding conversation: {conversation_id}")
    table = get_conversation_table_client(user_id)
    for attempt in range(2):
        # A consistent read returns the latest version for optimistic locking.
        item = table.get_item(
            Key={"PK": user_id, "SK": compose_conv_id(user_id, conversation_id)},
            ConsistentRead=True,
        ).get("Item")
        if item is None:
            raise RecordNotFoundError(
                f"No conversation found with id: {conversation_id}"
            )
        if not item.get("IsLargeMessage", False):
            message_map = json.loads(item["MessageMap"])
            break
        try:
            response = s3_client.get_object(
                Bucket=LARGE_MESSAGE_BUCKET, Key=item["LargeMessagePath"]
            )
        except s3_client.exceptions.NoSuchKey:
            # A concurrent write replaced the object after the item was read.
            if attempt == 1:
                raise
            continue
        message_map = json.loads(response["Body"].read().decode("utf-8"))
        break

    conv = ConversationModel(
        id=decompose_conv_id(item["SK"]),
        create_time=float(item["CreateTime"]),
        title=item["Title"],
        total_price=item.get("TotalPrice", 0),
        message_map={k: MessageModel.model_validate(v) for k, v in message_map.items()},
        last_message_id=item["LastMessageId"],
        bot_id=item["BotId"] if "BotId" in item else None,
        should_continue=item.get("ShouldContinue", False),
        version=int(item.get("Version", 0)),
    )
    conv.mark_stored()
    logger.info("Found conversation: %s", conv.id)
    return conv


def delete_conversation_by_id(user_id: str, conversation_id: str):
    logger.info(f"Deleting conversation: {conversation_id}")
    table = get_conversation_table_client(user_id)

    try:
        # Check if the conversation has a large message map
        response = table.get_item(
            Key={"PK": user_id, "SK": compose_conv_id(user_id, conversation_id)},
            ProjectionExpression="IsLargeMessage, LargeMessagePath",
        )

        item = response.get("Item")
        if item and item.get("IsLargeMessage", False):
            _delete_large_messages(user_id, conversation_id)

        # Delete the conversation from DynamoDB
        response = table.delete_item(
            Key={"PK": user_id, "SK": compose_conv_id(user_id, conversation_id)},
            ConditionExpression="attribute_exists(PK) AND attribute_exists(SK)",
        )
        delete_related_documents(
            user_id=user_id,
            conversation_id=conversation_id,
        )

    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise RecordNotFoundError(
                f"Conversation with id {conversation_id} not found"
            )
        else:
            raise e

    return response


def delete_conversation_by_user_id(user_id: str):
    logger.info(f"Deleting ALL conversations for user: {user_id}")
    table = get_conversation_table_client(user_id)

    query_params = {
        "KeyConditionExpression": Key("PK").eq(user_id)
        # NOTE: Need SK to fetch only conversations
        & Key("SK").begins_with(f"{user_id}#CONV#"),
        "ProjectionExpression": "SK, IsLargeMessage, LargeMessagePath",
    }

    def delete_batch(batch):
        with table.batch_writer() as writer:
            for item in batch:
                writer.delete_item(Key={"PK": user_id, "SK": item["SK"]})

    def delete_large_messages(items):
        for item in items:
            if item.get("IsLargeMessage", False):
                _delete_large_messages(user_id, decompose_conv_id(item["SK"]))

    try:
        response = table.query(
            **query_params,
        )

        while True:
            items = response.get("Items", [])
            delete_large_messages(items)

            for i in range(0, len(items), TRANSACTION_BATCH_WRITE_SIZE):
                batch = items[i : i + TRANSACTION_BATCH_WRITE_SIZE]
                delete_batch(batch)

            # Check if next page exists
            if "LastEvaluatedKey" not in response:
                break

            # Load next page
            query_params["ExclusiveStartKey"] = response["LastEvaluatedKey"]
            response = table.query(
                **query_params,
            )

        delete_related_documents(user_id=user_id)

    except ClientError as e:
        logger.error(f"An error occurred: {e.response['Error']['Message']}")
        raise e


def change_conversation_title(user_id: str, conversation_id: str, new_title: str):
    logger.info("Updating the title of conversation %s", conversation_id)
    table = get_conversation_table_client(user_id)

    try:
        response = table.update_item(
            Key={
                "PK": user_id,
                "SK": compose_conv_id(user_id, conversation_id),
            },
            # Bump the version so that a concurrent write keeps the new title.
            UpdateExpression="SET Title = :t ADD Version :one",
            ExpressionAttributeValues={":t": new_title, ":one": 1},
            ReturnValues="UPDATED_NEW",
            ConditionExpression="attribute_exists(PK) AND attribute_exists(SK)",
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise RecordNotFoundError(
                f"Conversation with id {conversation_id} not found"
            )
        else:
            raise e

    return response


def update_feedback(
    user_id: str, conversation_id: str, message_id: str, feedback: FeedbackModel
):
    logger.info(f"Updating feedback for conversation: {conversation_id}")
    conv = find_conversation_by_id(user_id, conversation_id)
    conv.message_map[message_id].feedback = feedback
    # Store the whole conversation so that large message maps stay in S3.
    store_conversation(user_id, conv)


def store_related_documents(
    user_id: str,
    conversation_id: str,
    related_documents: list[RelatedDocumentModel],
):
    table = get_conversation_table_client(user_id)
    with table.batch_writer() as writer:
        for related_document in related_documents:
            item_params = {
                "PK": user_id,
                "SK": compose_related_document_source_id(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    source_id=related_document.source_id,
                ),
                "SourceName": related_document.source_name,
                "SourceLink": related_document.source_link,
                "Content": related_document.content.model_dump(by_alias=True),
            }
            if related_document.page_number is not None:
                item_params["PageNumber"] = related_document.page_number
            writer.put_item(Item=item_params)


def find_related_documents_by_conversation_id(
    user_id: str,
    conversation_id: str,
) -> list[RelatedDocumentModel]:
    table = get_conversation_table_client(user_id)
    related_documents: list[RelatedDocumentModel] = []

    last_evaluated_key = None
    while True:
        response = table.query(
            KeyConditionExpression=(
                Key("PK").eq(user_id)
                & Key("SK").begins_with(
                    f"{user_id}#RELATED_DOCUMENT#{conversation_id}#"
                )
            ),
            ScanIndexForward=False,
            **(
                {
                    "ExclusiveStartKey": last_evaluated_key,
                }
                if last_evaluated_key is not None
                else {}
            ),
        )
        related_documents.extend(
            RelatedDocumentModel(
                content=TypeAdapter(ToolResultModel).validate_python(item["Content"]),
                source_id=decompose_related_document_source_id(composed_id=item["SK"]),
                source_name=item["SourceName"],
                source_link=item["SourceLink"],
                page_number=item.get("PageNumber"),
            )
            for item in response.get("Items") or []
        )

        last_evaluated_key = response.get("LastEvaluatedKey")
        if last_evaluated_key is None:
            break

    return related_documents


def find_related_document_by_id(
    user_id: str,
    conversation_id: str,
    source_id: str,
) -> RelatedDocumentModel:
    table = get_conversation_table_client(user_id)
    response = table.query(
        IndexName="SKIndex",
        KeyConditionExpression=(
            Key("SK").eq(
                compose_related_document_source_id(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    source_id=source_id,
                )
            )
        ),
    )
    if len(response["Items"]) == 0:
        raise RecordNotFoundError(
            f"No related document found with id: {conversation_id}#{source_id}"
        )

    item = response["Items"][0]
    return RelatedDocumentModel(
        content=TypeAdapter(ToolResultModel).validate_python(item["Content"]),
        source_id=source_id,
        source_name=item["SourceName"],
        source_link=item["SourceLink"],
        page_number=item.get("PageNumber"),
    )


def delete_related_documents(user_id: str, conversation_id: str | None = None):
    table = get_conversation_table_client(user_id)
    sort_keys: list[str] = []

    last_evaluated_key = None
    while True:
        response = table.query(
            KeyConditionExpression=(
                Key("PK").eq(user_id)
                & Key("SK").begins_with(
                    f"{user_id}#RELATED_DOCUMENT#{conversation_id}#"
                    if conversation_id
                    else f"{user_id}#RELATED_DOCUMENT#"
                )
            ),
            ProjectionExpression="SK",
            ScanIndexForward=False,
            **(
                {
                    "ExclusiveStartKey": last_evaluated_key,
                }
                if last_evaluated_key is not None
                else {}
            ),
        )
        sort_keys.extend(item["SK"] for item in response.get("Items") or [])

        last_evaluated_key = response.get("LastEvaluatedKey")
        if last_evaluated_key is None:
            break

    with table.batch_writer() as writer:
        for sort_key in sort_keys:
            writer.delete_item(
                Key={
                    "PK": user_id,
                    "SK": sort_key,
                },
            )
