import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from app.repositories import common


class TestAssumedRoleResourceCache(unittest.TestCase):
    def setUp(self):
        common._RESOURCE_CACHE.clear()
        self.sts = MagicMock()
        self.expiration = datetime.now(timezone.utc) + timedelta(hours=1)
        self.sts.assume_role.side_effect = lambda **_: {
            "Credentials": {
                "AccessKeyId": "a",
                "SecretAccessKey": "s",
                "SessionToken": "t",
                "Expiration": self.expiration,
            }
        }
        self.patches = [
            patch.dict(common.os.environ, {"AWS_EXECUTION_ENV": "AWS_Lambda"}),
            patch.object(common.boto3, "client", return_value=self.sts),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        common._RESOURCE_CACHE.clear()

    def test_reuses_credentials_per_table_and_user(self):
        first = common._get_aws_resource("dynamodb", "table", "user")
        again = common._get_aws_resource("dynamodb", "table", "user")
        other = common._get_aws_resource("dynamodb", "table", "other")

        self.assertIs(first, again)
        self.assertIsNot(first, other)
        self.assertEqual(self.sts.assume_role.call_count, 2)

    def test_assumes_the_role_again_before_the_credentials_expire(self):
        self.expiration = datetime.now(timezone.utc) + timedelta(minutes=1)
        common._get_aws_resource("dynamodb", "table", "user")
        common._get_aws_resource("dynamodb", "table", "user")
        self.assertEqual(self.sts.assume_role.call_count, 2)

    def test_scopes_the_policy_to_the_user(self):
        common._get_aws_resource("dynamodb", "table", "user")
        policy = self.sts.assume_role.call_args.kwargs["Policy"]
        self.assertIn('"dynamodb:LeadingKeys": ["user*"]', policy)
        self.assertIn("arn:aws:dynamodb:", policy)

    def test_does_not_share_resources_between_threads(self):
        import threading

        mine = common._get_aws_resource("dynamodb", "table", "user")
        other = []
        thread = threading.Thread(
            target=lambda: other.append(
                common._get_aws_resource("dynamodb", "table", "user")
            )
        )
        thread.start()
        thread.join()
        self.assertIsNot(mine, other[0])

    def test_bounds_the_cache(self):
        for i in range(common.RESOURCE_CACHE_SIZE + 3):
            common._get_aws_resource("dynamodb", "table", f"user{i}")
        self.assertEqual(len(common._RESOURCE_CACHE), common.RESOURCE_CACHE_SIZE)
