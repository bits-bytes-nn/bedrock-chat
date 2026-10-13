import unittest
from unittest.mock import MagicMock, patch

import pytest
from app.repositories.common import compose_sk, get_bot_table_client
from app.repositories.custom_bot import count_dedicated_knowledge_bases
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
        with patch.object(
            bot_usecase, "validate_external_resource_references"
        ), patch.object(bot_usecase, "validate_new_bot_id"), patch.object(
            bot_usecase, "_update_s3_documents_by_diff"
        ) as move_files:
            with self.assertRaises(ValueError):
                bot_usecase.create_new_bot(self.user, bot_input)
        move_files.assert_not_called()
