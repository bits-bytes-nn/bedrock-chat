import os

import boto3
import pytest
from moto import mock_aws

# Some modules create boto3 clients at import time, which needs a region. The tests
# that call AWS are marked with `aws` and are excluded by default.
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("DOCUMENT_BUCKET", "test-document-bucket")
# Tables used by the `dynamodb_tables` fixture. Read by app.repositories.common at
# import time, so they must be set before the app is imported.
os.environ.setdefault("REGION", "us-east-1")
os.environ.setdefault("CONVERSATION_TABLE_NAME", "test-conversation-table")
os.environ.setdefault("BOT_TABLE_NAME", "test-bot-table")


def pytest_configure(config):
    # Clients created at import time keep the credentials they found, and moto does
    # not replace them. Without fake credentials, a local profile would be used and
    # its errors printed. Only the `aws` tests need real credentials.
    if "not aws" not in config.option.markexpr:
        return
    for name in ("AWS_PROFILE", "AWS_DEFAULT_PROFILE"):
        os.environ.pop(name, None)
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ.pop("AWS_SESSION_TOKEN", None)
    os.environ["AWS_CONFIG_FILE"] = os.devnull
    os.environ["AWS_SHARED_CREDENTIALS_FILE"] = os.devnull


def _string_key(name: str) -> dict:
    return {"AttributeName": name, "AttributeType": "S"}


def _create_tables() -> None:
    """Create the tables with the keys and indexes in cdk/lib/constructs/database.ts."""
    # Use the names the app read at import time; other tests may change the env.
    from app.repositories import common

    dynamodb = boto3.client("dynamodb", region_name=common.REGION)
    dynamodb.create_table(
        TableName=common.CONVERSATION_TABLE_NAME,
        BillingMode="PAY_PER_REQUEST",
        AttributeDefinitions=[_string_key("PK"), _string_key("SK")],
        KeySchema=[
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
    )

    def gsi(name: str, hash_key: str, range_key: str | None = None) -> dict:
        key_schema = [{"AttributeName": hash_key, "KeyType": "HASH"}]
        if range_key:
            key_schema.append({"AttributeName": range_key, "KeyType": "RANGE"})
        return {
            "IndexName": name,
            "KeySchema": key_schema,
            "Projection": {"ProjectionType": "ALL"},
        }

    def lsi(name: str, range_key: str) -> dict:
        return {
            "IndexName": name,
            "KeySchema": [
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": range_key, "KeyType": "RANGE"},
            ],
            "Projection": {"ProjectionType": "ALL"},
        }

    dynamodb.create_table(
        TableName=common.BOT_TABLE_NAME,
        BillingMode="PAY_PER_REQUEST",
        AttributeDefinitions=[
            _string_key("PK"),
            _string_key("SK"),
            _string_key("IsStarred"),
            {"AttributeName": "LastUsedTime", "AttributeType": "N"},
            _string_key("BotId"),
            _string_key("SharedScope"),
            _string_key("SharedStatus"),
            _string_key("ItemType"),
            _string_key("SyncStatus"),
        ],
        KeySchema=[
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
        LocalSecondaryIndexes=[
            lsi("StarredIndex", "IsStarred"),
            lsi("LastUsedTimeIndex", "LastUsedTime"),
        ],
        GlobalSecondaryIndexes=[
            gsi("BotIdIndex", "BotId"),
            gsi("SharedScopeIndex", "SharedScope", "SharedStatus"),
            gsi("ItemTypeIndex", "ItemType"),
            gsi("SyncStatusIndex", "SyncStatus"),
        ],
    )


@pytest.fixture
def dynamodb_tables():
    """Run the test against in-memory DynamoDB tables (moto)."""
    with mock_aws():
        _create_tables()
        yield
