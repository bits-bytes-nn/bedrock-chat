import io
from unittest.mock import patch

import pytest
from botocore.response import StreamingBody
from botocore.stub import Stubber
from embedding_statemachine.bedrock_knowledge_base import (
    bootstrap_state_machine,
    lock,
)
from tests.test_repositories.utils.bot_factory import create_test_private_bot

KEY = ".temp/.lock.my-lock"


@pytest.fixture
def s3():
    with Stubber(lock.s3) as stubber:
        yield stubber
        stubber.assert_no_pending_responses()


def _acquire(owner: str = "owner-1"):
    return lock.handler(
        {"Action": "Acquire", "LockName": "My-Lock", "Owner": owner}, None
    )


def _put_params(owner: str = "owner-1") -> dict:
    return {
        "Bucket": lock.DOCUMENT_BUCKET,
        "Key": KEY,
        "IfNoneMatch": "*",
        "Body": owner,
    }


def _lock_file(owner: str) -> dict:
    body = owner.encode()
    return {"Body": StreamingBody(io.BytesIO(body), len(body)), "ETag": '"etag-1"'}


def test_acquire_creates_lock_file(s3):
    s3.add_response("put_object", {"ETag": '"etag-1"'}, _put_params())

    assert _acquire() == {"LockId": '"etag-1"'}


def test_acquire_retried_by_same_owner_returns_lock(s3):
    # A retry after a lost response finds the lock file it created itself.
    s3.add_client_error(
        "put_object", "PreconditionFailed", expected_params=_put_params("owner-1")
    )
    s3.add_response(
        "get_object",
        _lock_file("owner-1"),
        {"Bucket": lock.DOCUMENT_BUCKET, "Key": KEY},
    )

    assert _acquire("owner-1") == {"LockId": '"etag-1"'}


@pytest.mark.parametrize(
    "stub_get",
    [
        pytest.param(
            lambda s3: s3.add_response("get_object", _lock_file("owner-2")),
            id="other-owner",
        ),
        pytest.param(
            lambda s3: s3.add_client_error("get_object", "NoSuchKey"),
            id="released-meanwhile",
        ),
    ],
)
def test_acquire_held_lock_raises_retry(s3, stub_get):
    s3.add_client_error("put_object", "PreconditionFailed")
    stub_get(s3)

    with pytest.raises(lock.RetryException):
        _acquire("owner-1")


def test_acquire_conflict_raises_retry(s3):
    s3.add_client_error("put_object", "ConditionalRequestConflict")

    with pytest.raises(lock.RetryException):
        _acquire()


def test_release_deletes_only_matching_lock(s3):
    s3.add_response(
        "delete_object",
        {},
        {"Bucket": lock.DOCUMENT_BUCKET, "Key": KEY, "IfMatch": '"etag-1"'},
    )

    lock.handler(
        {"Action": "Release", "LockName": "My-Lock", "LockId": '"etag-1"'}, None
    )


def test_release_of_replaced_lock_succeeds(s3):
    s3.add_client_error("delete_object", "PreconditionFailed")

    lock.handler(
        {"Action": "Release", "LockName": "My-Lock", "LockId": '"etag-1"'}, None
    )


def test_invalid_action_raises():
    with pytest.raises(Exception, match="Invalid action"):
        lock.handler({"Action": "Steal"}, None)


@pytest.fixture
def repository():
    with (
        patch.object(bootstrap_state_machine, "find_bot_by_id") as find_bot,
        patch.object(bootstrap_state_machine, "find_queued_bots") as find_queued,
        patch.object(
            bootstrap_state_machine, "find_shared_knowledge_bases", return_value=[]
        ) as find_shared,
    ):
        find_bot.side_effect = lambda bot_id: create_test_private_bot(
            bot_id, False, "user1"
        )
        yield find_bot, find_queued, find_shared


def test_bootstrap_reads_queued_bots_from_event(repository):
    find_bot, find_queued, find_shared = repository

    output = bootstrap_state_machine.handler(
        {
            "QueuedBots": [
                {
                    "OwnerUserId": "user1",
                    "BotId": "bot1",
                    "FilesDiff": {"Added": ["a.txt"]},
                    "SyncSharedKnowledgeBasesRequired": False,
                },
                # Entries without ids are skipped.
                {"BotId": "bot2"},
            ]
        },
        None,
    )

    find_bot.assert_called_once_with("bot1")
    find_queued.assert_not_called()
    find_shared.assert_not_called()
    assert output["SharedKnowledgeBases"] is None
    [queued] = output["QueuedBots"]
    assert queued["OwnerUserId"] == "user1"
    assert queued["BotId"] == "bot1"
    assert queued["FilesDiff"] == {"Added": ["a.txt"], "Unchanged": [], "Deleted": []}


def test_bootstrap_reads_queued_bots_from_db(repository):
    find_bot, find_queued, find_shared = repository
    find_queued.return_value = [create_test_private_bot("bot3", False, "user3")]

    output = bootstrap_state_machine.handler({}, None)

    find_bot.assert_not_called()
    # Bots from the DB always resync the shared Knowledge Bases.
    find_shared.assert_called_once()
    assert output["SharedKnowledgeBases"] == []
    [queued] = output["QueuedBots"]
    assert (queued["OwnerUserId"], queued["BotId"]) == ("user3", "bot3")
    assert "FilesDiff" not in queued
