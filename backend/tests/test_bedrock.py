import os
import sys

os.environ["REGION"] = "us-west-2"
os.environ["BEDROCK_REGION"] = "us-west-2"
os.environ["ENABLE_BEDROCK_GLOBAL_INFERENCE"] = "true"
os.environ["ENABLE_BEDROCK_CROSS_REGION_INFERENCE"] = "true"

sys.path.append(".")

import unittest
from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError

from app import bedrock
from app.bedrock import get_model_id
from app.routes.schemas.conversation import type_model_name

MODEL: type_model_name = "claude-v5.5-haiku"


class TestGetModelId(unittest.TestCase):
    PROFILES = {
        "global.anthropic.claude-sonnet-4-6": frozenset(
            {"arn:aws:bedrock:::foundation-model/anthropic.claude-sonnet-4-6"}
        ),
        "us.anthropic.claude-sonnet-4-6": frozenset(
            {
                "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-sonnet-4-6",
                "arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-sonnet-4-6",
            }
        ),
        "us.amazon.nova-pro-v1:0": frozenset(
            {"arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-pro-v1:0"}
        ),
        "apac.amazon.nova-pro-v1:0": frozenset(
            {"arn:aws:bedrock:ap-northeast-2::foundation-model/amazon.nova-pro-v1:0"}
        ),
        # Named like a profile of the model, but routes to another one.
        "us.mistral.mistral-large-2402-v1:0": frozenset(
            {"arn:aws:bedrock:us-east-1::foundation-model/mistral.mistral-small"}
        ),
    }

    def get_model_id(self, model, **kwargs) -> str:
        with patch.object(
            bedrock, "_list_system_inference_profiles", return_value=self.PROFILES
        ):
            return get_model_id(model, bedrock_region="us-east-1", **kwargs)

    def test_prefers_global_profile(self):
        self.assertEqual(
            self.get_model_id(
                "claude-v4.6-sonnet", enable_global=True, enable_cross_region=True
            ),
            "global.anthropic.claude-sonnet-4-6",
        )

    def test_uses_geographic_profile_without_global(self):
        self.assertEqual(
            self.get_model_id(
                "claude-v4.6-sonnet", enable_global=False, enable_cross_region=True
            ),
            "us.anthropic.claude-sonnet-4-6",
        )

    def test_falls_back_to_geographic_profile_when_global_is_missing(self):
        self.assertEqual(
            self.get_model_id(
                "amazon-nova-pro", enable_global=True, enable_cross_region=True
            ),
            "apac.amazon.nova-pro-v1:0",
        )

    def test_uses_base_model_id_when_profiles_are_disabled(self):
        with patch.object(bedrock, "_list_system_inference_profiles") as profiles:
            model_id = get_model_id(
                "claude-v4.6-sonnet", enable_global=False, enable_cross_region=False
            )

        self.assertEqual(model_id, "anthropic.claude-sonnet-4-6")
        profiles.assert_not_called()

    def test_uses_base_model_id_without_a_profile_that_routes_to_it(self):
        self.assertEqual(
            self.get_model_id(
                "mistral-large", enable_global=True, enable_cross_region=True
            ),
            "mistral.mistral-large-2402-v1:0",
        )

    def test_tries_global_profile_when_lookup_fails(self):
        with patch.object(
            bedrock,
            "_list_system_inference_profiles",
            side_effect=ClientError(
                {"Error": {"Code": "AccessDeniedException", "Message": "denied"}},
                "ListInferenceProfiles",
            ),
        ):
            model_id = get_model_id(
                "claude-v4.6-sonnet",
                enable_global=True,
                enable_cross_region=True,
                bedrock_region="us-east-1",
            )

        self.assertEqual(model_id, "global.anthropic.claude-sonnet-4-6")

    def test_rejects_retired_model(self):
        with self.assertRaises(ValueError):
            self.get_model_id(
                "claude-v3.7-sonnet", enable_global=True, enable_cross_region=True
            )


class TestListInferenceProfiles(unittest.TestCase):
    def test_reads_the_model_arns_of_every_page(self):
        arn = "arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-pro-v1:0"
        client = MagicMock()
        client.list_inference_profiles.side_effect = [
            {
                "inferenceProfileSummaries": [
                    {"inferenceProfileId": "us.a", "models": [{"modelArn": arn}]}
                ],
                "nextToken": "t",
            },
            {
                "inferenceProfileSummaries": [
                    {"inferenceProfileId": "eu.b", "models": []}
                ]
            },
        ]
        bedrock._list_system_inference_profiles.cache_clear()
        with patch.object(bedrock.boto3, "client", return_value=client):
            profiles = bedrock._list_system_inference_profiles("test-region")
        bedrock._list_system_inference_profiles.cache_clear()

        self.assertEqual(profiles, {"us.a": frozenset({arn}), "eu.b": frozenset()})
        self.assertEqual(
            client.list_inference_profiles.call_args.kwargs["nextToken"], "t"
        )


if __name__ == "__main__":
    unittest.main()
