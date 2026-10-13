import unittest
from unittest.mock import MagicMock

from app.repositories import conversation_search
from app.user import User


class TestFindConversationsByQuery(unittest.TestCase):
    def test_logs_a_malformed_hit_without_its_text(self):
        hit = {
            "_id": "hit",
            "_source": {"SK": "user#CONV#c", "Title": {"text": "private text"}},
        }
        client = MagicMock()
        client.search.return_value = {"hits": {"hits": [hit]}}
        user = User(id="user", name="user", email="user@example.com", groups=[])

        with self.assertLogs(conversation_search.logger, "ERROR") as logs:
            result = conversation_search.find_conversations_by_query(
                "q", user, client=client
            )

        self.assertEqual(result, [])
        self.assertIn("hit", logs.output[0])
        self.assertNotIn("private text", logs.output[0])


if __name__ == "__main__":
    unittest.main()
