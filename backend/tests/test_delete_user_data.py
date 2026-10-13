import sys
import unittest
from unittest.mock import patch

import pytest
from app.repositories.common import compose_sk, get_bot_table_client
from app.repositories.conversation import find_conversation_by_user_id

sys.path.insert(0, "scripts")
import delete_user_data  # noqa: E402


@pytest.mark.usefixtures("dynamodb_tables")
class TestDeleteUserData(unittest.TestCase):
    def setUp(self):
        table = get_bot_table_client()
        for pk, sk in (
            ("user", compose_sk("b1", "bot")),
            ("user", compose_sk("b2", "alias")),
            ("other", compose_sk("b3", "bot")),
        ):
            table.put_item(Item={"PK": pk, "SK": sk})

    def run_script(self, *args: str):
        with patch.object(sys, "argv", ["delete_user_data.py", *args]):
            delete_user_data.main()

    def remaining(self, user_id: str) -> list[str]:
        return [k["SK"] for k in delete_user_data._bot_table_keys(user_id)]

    def test_lists_without_deleting(self):
        self.run_script("user")
        self.assertEqual(len(self.remaining("user")), 2)

    def test_deletes_only_the_users_items(self):
        with patch.object(
            delete_user_data, "delete_conversation_by_user_id"
        ) as delete_conversations:
            self.run_script("user", "--yes")
        delete_conversations.assert_called_once_with("user")
        self.assertEqual(self.remaining("user"), [])
        self.assertEqual(len(self.remaining("other")), 1)
        self.assertEqual(find_conversation_by_user_id("user"), [])
