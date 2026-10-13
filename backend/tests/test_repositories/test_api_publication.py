import os
import sys
import unittest

import pytest
from pprint import pprint

sys.path.append(".")

from app.repositories.api_publication import (
    create_api_key,
    delete_api_key,
    find_api_key_by_id,
    find_stack_by_bot_id,
    find_usage_plan_by_id,
)

# A published API to test against, from the ApiPublishmentStack<bot id> outputs.
usage_plan_id = os.environ.get("TEST_PUBLISHED_API_USAGE_PLAN_ID", "")
bot_id = os.environ.get("TEST_PUBLISHED_API_BOT_ID", "")


pytestmark = pytest.mark.aws


class TestApiGateway(unittest.TestCase):
    def setUp(self):
        if not usage_plan_id:
            self.skipTest("TEST_PUBLISHED_API_USAGE_PLAN_ID is not set")

    def test_find_usage_plan_by_id(self):
        plan = find_usage_plan_by_id(usage_plan_id)
        pprint(plan)
        self.assertTrue(plan is not None)

    def test_find_api_key_by_id(self):
        plan = find_usage_plan_by_id(usage_plan_id)
        key_id = plan.key_ids[0]
        key = find_api_key_by_id(key_id, include_value=True)
        pprint(key)
        self.assertTrue(key is not None)
        self.assertEqual(key.id, key_id)
        self.assertEqual(key.enabled, True)

    def test_create_delete_api_key(self):
        res = create_api_key(usage_plan_id, "description")
        key = find_api_key_by_id(res.id, include_value=True)
        self.assertEqual(key.id, res.id)
        self.assertEqual(key.enabled, True)
        self.assertEqual(key.description, "description")
        delete_api_key(key.id)


class TestCloudformation(unittest.TestCase):
    def setUp(self):
        if not bot_id:
            self.skipTest("TEST_PUBLISHED_API_BOT_ID is not set")

    def test_find_stack_by_bot_id(self):
        stack = find_stack_by_bot_id(bot_id)
        pprint(stack)
        self.assertTrue(stack is not None)


if __name__ == "__main__":
    unittest.main()
