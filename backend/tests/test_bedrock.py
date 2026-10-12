import os
import sys

os.environ["REGION"] = "us-west-2"
os.environ["BEDROCK_REGION"] = "us-west-2"
os.environ["ENABLE_BEDROCK_GLOBAL_INFERENCE"] = "true"
os.environ["ENABLE_BEDROCK_CROSS_REGION_INFERENCE"] = "true"

sys.path.append(".")

import unittest
from unittest.mock import patch

from botocore.exceptions import ClientError

from app import bedrock
from app.bedrock import get_model_id
from app.routes.schemas.conversation import type_model_name

MODEL: type_model_name = "claude-v5.5-haiku"


class TestGetModelId(unittest.TestCase):
    PROFILES = frozenset(
        {
            "global.anthropic.claude-sonnet-4-6",
            "us.anthropic.claude-sonnet-4-6",
            "us.amazon.nova-pro-v1:0",
            "apac.amazon.nova-pro-v1:0",
        }
    )

    def get_model_id(self, model, **kwargs) -> str:
        with patch.object(
            bedrock, "_list_system_inference_profile_ids", return_value=self.PROFILES
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
        with patch.object(bedrock, "_list_system_inference_profile_ids") as profiles:
            model_id = get_model_id(
                "claude-v4.6-sonnet", enable_global=False, enable_cross_region=False
            )

        self.assertEqual(model_id, "anthropic.claude-sonnet-4-6")
        profiles.assert_not_called()

    def test_uses_base_model_id_without_profile(self):
        self.assertEqual(
            self.get_model_id(
                "mistral-large", enable_global=True, enable_cross_region=True
            ),
            "mistral.mistral-large-2402-v1:0",
        )

    def test_tries_global_profile_when_lookup_fails(self):
        with patch.object(
            bedrock,
            "_list_system_inference_profile_ids",
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


if __name__ == "__main__":
    unittest.main()
