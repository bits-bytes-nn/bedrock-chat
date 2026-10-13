import unittest
from unittest.mock import MagicMock, patch

from app.repositories import knowledge_base
from botocore.exceptions import ClientError


class TestGetKnowledgeBaseType(unittest.TestCase):
    def setUp(self):
        knowledge_base.get_knowledge_base_type.cache_clear()

    def test_reads_the_type_once_per_knowledge_base(self):
        client = MagicMock()
        client.get_knowledge_base.return_value = {
            "knowledgeBase": {"knowledgeBaseConfiguration": {"type": "KENDRA"}}
        }
        with patch.object(
            knowledge_base, "get_bedrock_agent_client", return_value=client
        ):
            self.assertEqual(knowledge_base.get_knowledge_base_type("kb"), "KENDRA")
            self.assertEqual(knowledge_base.get_knowledge_base_type("kb"), "KENDRA")
        client.get_knowledge_base.assert_called_once_with(knowledgeBaseId="kb")

    def test_raises_instead_of_guessing_the_type(self):
        client = MagicMock()
        client.get_knowledge_base.side_effect = ClientError(
            {"Error": {"Code": "AccessDeniedException"}}, "GetKnowledgeBase"
        )
        with patch.object(
            knowledge_base, "get_bedrock_agent_client", return_value=client
        ):
            with self.assertRaises(ClientError):
                knowledge_base.get_knowledge_base_type("kb")
