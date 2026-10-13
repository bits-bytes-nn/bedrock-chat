import unittest

import boto3
from moto import mock_aws

from app.utils import delete_s3_prefix


class TestDeleteS3Prefix(unittest.TestCase):
    @mock_aws
    def test_deletes_more_than_one_page(self):
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="test-bucket")
        for i in range(1005):
            s3.put_object(Bucket="test-bucket", Key=f"user/bot/{i}", Body=b"")
        s3.put_object(Bucket="test-bucket", Key="user/other/keep", Body=b"")

        delete_s3_prefix(s3, "test-bucket", "user/bot/")

        keys = [o["Key"] for o in s3.list_objects_v2(Bucket="test-bucket")["Contents"]]
        self.assertEqual(keys, ["user/other/keep"])
