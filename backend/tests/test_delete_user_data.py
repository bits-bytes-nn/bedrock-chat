import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import pytest
from app.repositories.common import compose_sk, get_bot_table_client
from app.repositories.conversation import (
    find_conversation_by_user_id,
    store_conversation,
)
from app.repositories.models.conversation import ConversationModel

SCRIPT = Path(__file__).parents[1] / "scripts" / "delete_user_data.py"
_spec = importlib.util.spec_from_file_location("delete_user_data", SCRIPT)
assert _spec is not None and _spec.loader is not None
delete_user_data = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(delete_user_data)


def conversation(conversation_id: str) -> ConversationModel:
    return ConversationModel(
        id=conversation_id,
        create_time=0,
        title="t",
        total_price=0,
        message_map={},
        last_message_id="",
        bot_id=None,
        should_continue=False,
    )


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
        store_conversation("user", conversation("c1"))
        store_conversation("other", conversation("c2"))

    def run_script(self, *args: str):
        with patch.object(sys, "argv", ["delete_user_data.py", *args]):
            delete_user_data.main()

    def remaining(self, user_id: str) -> list[str]:
        return [k["SK"] for k in delete_user_data._bot_table_keys(user_id)]

    def test_lists_without_deleting(self):
        self.run_script("user")

        self.assertEqual(len(self.remaining("user")), 2)
        self.assertEqual([c.id for c in find_conversation_by_user_id("user")], ["c1"])

    def test_deletes_only_the_users_items(self):
        self.run_script("user", "--yes")

        self.assertEqual(self.remaining("user"), [])
        self.assertEqual(find_conversation_by_user_id("user"), [])
        self.assertEqual(len(self.remaining("other")), 1)
        self.assertEqual([c.id for c in find_conversation_by_user_id("other")], ["c2"])
