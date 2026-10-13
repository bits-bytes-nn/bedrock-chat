import unittest
from unittest.mock import patch

import boto3
import pytest
from app.repositories import conversation as conversation_repository
from app.repositories.conversation import (
    change_conversation_title,
    find_conversation_by_id,
    find_conversation_by_user_id,
    store_conversation,
)
from app.repositories.models.conversation import (
    ConversationModel,
    FeedbackModel,
    MessageModel,
    TextContentModel,
    merge_conversations,
)


def message(parent: str | None, text: str = "hi") -> MessageModel:
    return MessageModel(
        role="user",
        content=[TextContentModel(content_type="text", body=text)],
        model="claude-v5.5-haiku",
        children=[],
        parent=parent,
        create_time=0,
        feedback=None,
        used_chunks=None,
        thinking_log=None,
    )


def conversation() -> ConversationModel:
    system = message(None, "")
    system.children = ["a"]
    return ConversationModel(
        id="c",
        create_time=0,
        title="New conversation",
        total_price=1.0,
        message_map={"system": system, "a": message("system")},
        last_message_id="a",
        bot_id=None,
        should_continue=False,
    )


def add_reply(conv: ConversationModel, message_id: str, price: float) -> None:
    conv.message_map[message_id] = message("a", message_id)
    conv.message_map["a"].children.append(message_id)
    conv.last_message_id = message_id
    conv.total_price += price


class TestMergeConversations(unittest.TestCase):
    def test_keeps_both_writers_changes(self):
        base = conversation()
        mine, theirs = base.model_copy(deep=True), base.model_copy(deep=True)
        add_reply(mine, "mine", 0.5)
        add_reply(theirs, "theirs", 0.25)
        theirs.message_map["a"].feedback = FeedbackModel(
            thumbs_up=True, category="", comment=""
        )
        theirs.title = "Generated title"

        merged = merge_conversations(base, mine, theirs)

        self.assertEqual(merged.message_map["a"].children, ["theirs", "mine"])
        self.assertIsNotNone(merged.message_map["a"].feedback)
        self.assertEqual(merged.title, "Generated title")
        self.assertEqual(merged.last_message_id, "mine")
        self.assertAlmostEqual(merged.total_price, 1.75)

    def test_applies_removals(self):
        base = conversation()
        add_reply(base, "old", 0)
        mine, theirs = base.model_copy(deep=True), base.model_copy(deep=True)
        del mine.message_map["old"]
        mine.message_map["a"].children.remove("old")

        merged = merge_conversations(base, mine, theirs)

        self.assertNotIn("old", merged.message_map)
        self.assertEqual(merged.message_map["a"].children, [])

    def test_mine_wins_when_both_change_the_same_field(self):
        base = conversation()
        mine, theirs = base.model_copy(deep=True), base.model_copy(deep=True)
        mine.title = "Mine"
        theirs.title = "Theirs"
        mine.message_map["a"].feedback = FeedbackModel(
            thumbs_up=True, category="mine", comment=""
        )
        theirs.message_map["a"].feedback = FeedbackModel(
            thumbs_up=False, category="theirs", comment=""
        )

        merged = merge_conversations(base, mine, theirs)

        self.assertEqual(merged.title, "Mine")
        self.assertEqual(merged.message_map["a"].feedback.category, "mine")

    def test_without_base_sums_prices_and_keeps_both_messages(self):
        mine, theirs = conversation(), conversation()
        add_reply(mine, "mine", 0.5)
        add_reply(theirs, "theirs", 0.25)

        merged = merge_conversations(None, mine, theirs)

        self.assertAlmostEqual(merged.total_price, 1.0 + 0.5 + 1.0 + 0.25)
        self.assertEqual(merged.message_map["a"].children, ["theirs", "mine"])
        self.assertEqual(merged.last_message_id, "mine")

    def test_mine_edit_restores_a_message_theirs_deleted(self):
        base = conversation()
        add_reply(base, "old", 0)
        mine, theirs = base.model_copy(deep=True), base.model_copy(deep=True)
        del theirs.message_map["old"]
        theirs.message_map["a"].children.remove("old")
        mine.message_map["old"].content[0].body = "edited"

        merged = merge_conversations(base, mine, theirs)

        self.assertEqual(merged.message_map["old"].content[0].body, "edited")

    def test_restored_message_is_linked_from_its_parent(self):
        base = conversation()
        add_reply(base, "old", 0)
        mine, theirs = base.model_copy(deep=True), base.model_copy(deep=True)
        del theirs.message_map["old"]
        theirs.message_map["a"].children.remove("old")
        mine.message_map["old"].content[0].body = "edited"

        merged = merge_conversations(base, mine, theirs)

        self.assertIn("old", merged.message_map["a"].children)

    def test_mine_removal_wins_over_a_child_theirs_added(self):
        base = conversation()
        add_reply(base, "old", 0)
        mine, theirs = base.model_copy(deep=True), base.model_copy(deep=True)
        theirs.message_map["child"] = message("old", "child")
        theirs.message_map["old"].children.append("child")
        del mine.message_map["old"]
        mine.message_map["a"].children.remove("old")

        merged = merge_conversations(base, mine, theirs)

        self.assertNotIn("old", merged.message_map)
        self.assertEqual(merged.message_map["a"].children, [])

    def test_last_message_points_to_a_message_that_survived(self):
        base = conversation()
        add_reply(base, "old", 0)
        mine, theirs = base.model_copy(deep=True), base.model_copy(deep=True)
        theirs.message_map["child"] = message("old", "child")
        theirs.message_map["old"].children.append("child")
        theirs.last_message_id = "child"
        del mine.message_map["old"]
        mine.message_map["a"].children.remove("old")
        mine.last_message_id = "a"

        merged = merge_conversations(base, mine, theirs)
        self.assertEqual(merged.last_message_id, "a")

        mine.last_message_id = "old"  # unchanged from base, so theirs wins
        merged = merge_conversations(base, mine, theirs)
        self.assertIn(merged.last_message_id, merged.message_map)

    def test_no_message_is_left_without_its_parent(self):
        base = conversation()
        add_reply(base, "old", 0)
        mine, theirs = base.model_copy(deep=True), base.model_copy(deep=True)
        theirs.message_map["child"] = message("old", "child")
        theirs.message_map["old"].children.append("child")
        del mine.message_map["old"]
        mine.message_map["a"].children.remove("old")

        merged = merge_conversations(base, mine, theirs)

        for message_id, node in merged.message_map.items():
            if node.parent is not None:
                self.assertIn(node.parent, merged.message_map, message_id)


@pytest.mark.usefixtures("dynamodb_tables")
class TestStoreConversationConcurrently(unittest.TestCase):
    def test_merges_a_concurrent_write(self):
        store_conversation("user", conversation())
        first = find_conversation_by_id("user", "c")
        second = find_conversation_by_id("user", "c")

        add_reply(first, "first", 0.5)
        store_conversation("user", first)
        add_reply(second, "second", 0.25)
        store_conversation("user", second)

        stored = find_conversation_by_id("user", "c")
        self.assertEqual(stored.message_map["a"].children, ["first", "second"])
        self.assertAlmostEqual(stored.total_price, 1.75)
        self.assertEqual(stored.version, 3)

    def test_keeps_a_title_set_while_answering(self):
        store_conversation("user", conversation())
        answering = find_conversation_by_id("user", "c")

        change_conversation_title("user", "c", "Generated title")
        add_reply(answering, "answer", 0.5)
        store_conversation("user", answering)

        stored = find_conversation_by_id("user", "c")
        self.assertEqual(stored.title, "Generated title")
        self.assertIn("answer", stored.message_map)

    def test_merges_large_conversations_without_losing_the_stored_object(self):
        bucket = "test-large-message-bucket"
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=bucket)
        with patch.object(conversation_repository, "LARGE_MESSAGE_BUCKET", bucket):
            store_conversation("user", conversation(), threshold=1)
            first = find_conversation_by_id("user", "c")
            second = find_conversation_by_id("user", "c")

            add_reply(first, "first", 0.5)
            store_conversation("user", first, threshold=1)
            add_reply(second, "second", 0.25)
            store_conversation("user", second, threshold=1)

            stored = find_conversation_by_id("user", "c")
            objects = s3.list_objects_v2(Bucket=bucket)["Contents"]

        self.assertEqual(stored.message_map["a"].children, ["first", "second"])
        # Only the object of the latest write is kept.
        self.assertEqual(len(objects), 1)

    def test_keeps_the_object_when_a_retried_write_finds_itself(self):
        bucket = "test-large-message-bucket"
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=bucket)
        get_table = conversation_repository.get_conversation_table_client

        class LostResponseTable:
            """Applies each write, then retries it as if the response was lost."""

            def __init__(self, table):
                self.table = table

            def put_item(self, **kwargs):
                self.table.put_item(**kwargs)
                return self.table.put_item(**kwargs)

            def __getattr__(self, name):
                return getattr(self.table, name)

        with patch.object(conversation_repository, "LARGE_MESSAGE_BUCKET", bucket):
            store_conversation("user", conversation(), threshold=1)
            answering = find_conversation_by_id("user", "c")
            add_reply(answering, "answer", 0.5)
            with patch.object(
                conversation_repository,
                "get_conversation_table_client",
                lambda user_id: LostResponseTable(get_table(user_id)),
            ):
                store_conversation("user", answering, threshold=1)

            stored = find_conversation_by_id("user", "c")

        self.assertIn("answer", stored.message_map)
        self.assertEqual(stored.version, answering.version)

    def test_lists_every_conversation_across_pages(self):
        for i in range(7):
            conv = conversation()
            conv.id = f"c{i}"
            store_conversation("user", conv)
        get_table = conversation_repository.get_conversation_table_client

        class OneItemPages:
            def __init__(self, table):
                self.table = table

            def query(self, **kwargs):
                return self.table.query(Limit=1, **kwargs)

        with patch.object(
            conversation_repository,
            "get_conversation_table_client",
            lambda user_id: OneItemPages(get_table(user_id)),
        ):
            listed = find_conversation_by_user_id("user")

        self.assertEqual({c.id for c in listed}, {f"c{i}" for i in range(7)})

    def test_upgrades_items_without_a_version(self):
        legacy = conversation()
        store_conversation("user", legacy)
        stored = find_conversation_by_id("user", "c")
        self.assertEqual(stored.version, 1)


@pytest.mark.usefixtures("dynamodb_tables")
class TestRelatedDocuments(unittest.TestCase):
    def test_finds_a_stored_document_by_its_key(self):
        from app.repositories.common import RecordNotFoundError
        from app.repositories.conversation import (
            find_related_document_by_id,
            store_related_documents,
        )
        from app.repositories.models.conversation import (
            RelatedDocumentModel,
            TextToolResultModel,
        )

        store_related_documents(
            "user",
            "c",
            [
                RelatedDocumentModel(
                    content=TextToolResultModel(text="body"),
                    source_id="s1",
                    source_name="doc.pdf",
                )
            ],
        )

        found = find_related_document_by_id("user", "c", "s1")
        self.assertEqual(found.source_name, "doc.pdf")
        with self.assertRaises(RecordNotFoundError):
            find_related_document_by_id("user", "c", "missing")


if __name__ == "__main__":
    unittest.main()
