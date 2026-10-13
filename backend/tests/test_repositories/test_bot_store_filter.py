import json
import unittest
from unittest.mock import MagicMock

from app.repositories import bot_store
from app.user import User


def search_bodies(user: User) -> list[str]:
    client = MagicMock()
    client.search.return_value = {"hits": {"hits": []}}
    bot_store.find_bots_by_query("q", user, client=client)
    bot_store.find_bots_sorted_by_usage_count(user, client=client)
    bot_store.find_random_bots(user, client=client)
    return [json.dumps(call.kwargs["body"]) for call in client.search.call_args_list]


class TestAccessibleBotsFilter(unittest.TestCase):
    def test_every_listing_applies_the_same_filter(self):
        user = User(id="u1", name="u1", email="u1@example.com", groups=["team"])
        expected = json.dumps(bot_store._accessible_bots_filter(user))
        for body in search_bodies(user):
            self.assertIn(expected, body)

    def test_non_admins_need_to_be_allowed_to_see_partial_bots(self):
        user = User(id="u1", name="u1", email="u1@example.com", groups=["team"])
        partial = bot_store._accessible_bots_filter(user)["bool"]["should"][2]
        allowed = partial["bool"]["must"][1]["bool"]["should"]
        self.assertIn({"term": {"AllowedCognitoUsers.keyword": "u1"}}, allowed)
        self.assertIn({"terms": {"AllowedCognitoGroups.keyword": ["team"]}}, allowed)

    def test_admins_see_every_partial_bot(self):
        admin = User(id="a", name="a", email="a@example.com", groups=["Admin"])
        partial = bot_store._accessible_bots_filter(admin)["bool"]["should"][2]
        self.assertEqual(partial, {"term": {"SharedScope.keyword": "partial"}})
