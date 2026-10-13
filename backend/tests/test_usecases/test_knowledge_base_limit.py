import unittest
from unittest.mock import MagicMock, patch

import pytest
from app.repositories.common import (
    LimitExceededError,
    compose_sk,
    get_bot_table_client,
)
from app.repositories.custom_bot import count_dedicated_knowledge_bases
from app.repositories.models.custom_bot_kb import (
    BedrockKnowledgeBaseModel,
    OpenSearchParamsModel,
    SearchParamsModel,
)
from app.usecases import bot as bot_usecase


@pytest.mark.usefixtures("dynamodb_tables")
class TestCountDedicatedKnowledgeBases(unittest.TestCase):
    def put(self, bot_id: str, kb_type: str | None, user_id: str = "user"):
        item = {"PK": user_id, "SK": compose_sk(bot_id, "bot")}
        if kb_type:
            item["BedrockKnowledgeBase"] = {"type": kb_type}
        get_bot_table_client().put_item(Item=item)

    def test_counts_the_users_other_dedicated_bots(self):
        self.put("a", "dedicated")
        self.put("b", "dedicated")
        self.put("c", "shared")
        self.put("d", None)
        self.put("e", "dedicated", user_id="other")
        get_bot_table_client().put_item(
            Item={"PK": "user", "SK": compose_sk("a", "alias")}
        )

        self.assertEqual(count_dedicated_knowledge_bases("user", "new"), 2)
        self.assertEqual(count_dedicated_knowledge_bases("user", "a"), 1)


class TestDedicatedKnowledgeBaseLimit(unittest.TestCase):
    def setUp(self):
        self.user = MagicMock(id="user")
        self.user.is_admin.return_value = False
        self.patches = [
            patch.object(bot_usecase, "MAX_DEDICATED_KNOWLEDGE_BASES_PER_USER", 2),
            patch.object(
                bot_usecase, "count_dedicated_knowledge_bases", return_value=2
            ),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def test_rejects_another_dedicated_knowledge_base(self):
        with self.assertRaises(ValueError):
            bot_usecase._check_dedicated_knowledge_base_limit(self.user, "new")

    def test_does_not_limit_admins(self):
        self.user.is_admin.return_value = True
        bot_usecase._check_dedicated_knowledge_base_limit(self.user, "new")

    def test_only_bots_with_sources_and_no_shared_or_existing_kb_count(self):
        uses = bot_usecase._uses_dedicated_knowledge_base
        self.assertTrue(uses(True, None))
        self.assertTrue(uses(True, MagicMock(exist_knowledge_base_id=None, type=None)))
        self.assertFalse(uses(False, None))
        self.assertFalse(
            uses(True, MagicMock(exist_knowledge_base_id=None, type="shared"))
        )
        self.assertFalse(
            uses(True, MagicMock(exist_knowledge_base_id="kb", type="dedicated"))
        )

    def test_create_is_rejected_before_files_are_moved(self):
        bot_input = MagicMock(id="new", bedrock_knowledge_base=None)
        bot_input.has_knowledge.return_value = True
        with (
            patch.object(bot_usecase, "validate_external_resource_references"),
            patch.object(bot_usecase, "validate_new_bot_id"),
            patch.object(bot_usecase, "_update_s3_documents_by_diff") as move_files,
        ):
            with self.assertRaises(ValueError):
                bot_usecase.create_new_bot(self.user, bot_input)
        move_files.assert_not_called()


class _FilesMoved(Exception):
    """Stops modify_owned_bot once the limit check has passed."""


def knowledge_base(kb_type: str) -> BedrockKnowledgeBaseModel:
    return BedrockKnowledgeBaseModel(
        type=kb_type,
        embeddings_model="titan_v2",
        open_search=OpenSearchParamsModel(analyzer=None),
        chunking_configuration=None,
        search_params=SearchParamsModel(max_results=10, search_type="hybrid"),
    )


@pytest.mark.usefixtures("dynamodb_tables")
class TestModifyOwnedBotLimit(unittest.TestCase):
    """The user is at the limit of 2 with the dedicated bots a and b."""

    def setUp(self):
        self.user = MagicMock(id="user")
        self.user.is_admin.return_value = False
        for bot_id, kb_type in (
            ("a", "dedicated"),
            ("b", "dedicated"),
            ("c", "shared"),
        ):
            get_bot_table_client().put_item(
                Item={
                    "PK": "user",
                    "SK": compose_sk(bot_id, "bot"),
                    "BedrockKnowledgeBase": {"type": kb_type},
                }
            )

    def modify(self, bot_id: str, current_type: str, new_type: str) -> None:
        """Modify the bot until it moves the files, right after the limit check."""
        bot = MagicMock(
            sync_status="SUCCEEDED",
            owner_user_id="user",
            bedrock_knowledge_base=knowledge_base(current_type),
        )
        modify_input = MagicMock()
        modify_input.knowledge.source_urls = ["https://example.com"]
        modify_input.bedrock_knowledge_base.model_dump.return_value = knowledge_base(
            new_type
        ).model_dump()
        self.move_files = MagicMock(side_effect=_FilesMoved)
        with (
            patch.object(bot_usecase, "MAX_DEDICATED_KNOWLEDGE_BASES_PER_USER", 2),
            patch.object(bot_usecase, "find_bot_by_id", return_value=bot),
            patch.object(bot_usecase, "validate_external_resource_references"),
            patch.object(bot_usecase, "_update_s3_documents_by_diff", self.move_files),
        ):
            try:
                bot_usecase.modify_owned_bot(self.user, bot_id, modify_input)
            except _FilesMoved:
                pass

    def test_existing_dedicated_bot_at_the_limit_is_editable(self):
        self.modify("a", "dedicated", "dedicated")
        self.move_files.assert_called_once()

    def test_switching_to_dedicated_at_the_limit_is_rejected_before_moving_files(self):
        with self.assertRaises(LimitExceededError):
            self.modify("c", "shared", "dedicated")
        self.move_files.assert_not_called()
