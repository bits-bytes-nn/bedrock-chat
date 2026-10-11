import pytest
import os
import sys

import boto3
from ulid import ULID

os.environ["REGION"] = "us-west-2"
os.environ["BEDROCK_REGION"] = "us-west-2"
os.environ["ENABLE_BEDROCK_GLOBAL_INFERENCE"] = "true"
os.environ["ENABLE_BEDROCK_CROSS_REGION_INFERENCE"] = "true"

sys.path.append(".")

import unittest
from pprint import pprint
from unittest.mock import patch

from botocore.exceptions import ClientError

from app import bedrock
from app.bedrock import call_converse_api, compose_args_for_converse_api, get_model_id
from app.repositories.models.conversation import SimpleMessageModel, TextContentModel
from app.repositories.models.custom_bot_guardrails import BedrockGuardrailsModel
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


@pytest.mark.aws
class TestCallConverseApi(unittest.TestCase):
    def test_call_converse_api_with_global_inference(self):
        """Actual LLM call using global inference profile"""
        message = SimpleMessageModel(
            role="user",
            content=[
                TextContentModel(
                    content_type="text",
                    body="Hello! Please respond with just 'Global inference works!'",
                )
            ],
        )

        # Use global inference supported model
        arg = compose_args_for_converse_api(
            [message],
            "claude-v5.5-haiku",
            stream=False,
        )

        # Verify modelId is global profile
        expected_model_id = "global.anthropic.claude-haiku-5-5"
        self.assertEqual(arg["modelId"], expected_model_id)

        # Actual API call
        response = call_converse_api(arg)

        # Verify basic response structure
        self.assertIn("output", response)
        self.assertIn("message", response["output"])
        self.assertIn("content", response["output"]["message"])

        print(f"Global inference response: {response['output']['message']['content']}")

    def test_call_converse_api_with_regional_fallback(self):
        """Actual LLM call with regional cross-region fallback"""
        message = SimpleMessageModel(
            role="user",
            content=[
                TextContentModel(
                    content_type="text",
                    body="Hello! Please respond with just 'Regional inference works!'",
                )
            ],
        )

        # Use non-global supported model
        arg = compose_args_for_converse_api(
            [message],
            "amazon-nova-pro",  # No global profile
            stream=False,
        )

        # Verify modelId is regional profile
        expected_model_id = "us.amazon.nova-pro-v1:0"
        self.assertEqual(arg["modelId"], expected_model_id)

        # Actual API call
        response = call_converse_api(arg)

        # Verify basic response structure
        self.assertIn("output", response)
        self.assertIn("message", response["output"])
        self.assertIn("content", response["output"]["message"])

        print(
            f"Regional inference response: {response['output']['message']['content']}"
        )

    def test_call_converse_api(self):
        message = SimpleMessageModel(
            role="user",
            content=[
                TextContentModel(
                    content_type="text",
                    body="Hello, World!",
                )
            ],
        )
        arg = compose_args_for_converse_api(
            [message],
            MODEL,
            stream=False,
        )

        response = call_converse_api(arg)
        pprint(response)


@pytest.mark.aws
class TestCallConverseApiWithGuardrails(unittest.TestCase):
    def setUp(self):
        # Note that the region must be the same as the one used in the bedrock client
        # https://github.com/aws/aws-sdk-js-v3/issues/6482
        self.bedrock_client = boto3.client("bedrock", region_name="us-east-1")
        self.guardrail_name = f"test-guardrail-{ULID()}"

        # Create dummy guardrail
        res = self.bedrock_client.create_guardrail(
            name=self.guardrail_name,
            description="Test guardrail for unit tests",
            contentPolicyConfig={
                "filtersConfig": [
                    {"type": "SEXUAL", "inputStrength": "LOW", "outputStrength": "LOW"},
                ]
            },
            blockedInputMessaging="blocked",
            blockedOutputsMessaging="blocked",
        )

        res_ver = self.bedrock_client.create_guardrail_version(
            guardrailIdentifier=res["guardrailArn"],
        )

        self.guardrail = BedrockGuardrailsModel(
            is_guardrail_enabled=True,
            hate_threshold=0,
            insults_threshold=0,
            sexual_threshold=1,
            violence_threshold=0,
            misconduct_threshold=0,
            grounding_threshold=0,
            relevance_threshold=0,
            guardrail_arn=res["guardrailArn"],
            guardrail_version=res_ver["version"],
            # guardrail_version="DRAFT",
        )
        self.guardrail_arn = res["guardrailArn"]

    def tearDown(self):
        print("Cleaning up...")
        # Delete dummy guardrail
        try:
            self.bedrock_client.delete_guardrail(guardrailIdentifier=self.guardrail_arn)

        except Exception as e:
            print(f"Error deleting guardrail: {e}")

    def test_call_converse_api_with_guardrails(self):
        message = SimpleMessageModel(
            role="user",
            content=[
                TextContentModel(
                    content_type="text",
                    body="Hello, World!",
                )
            ],
        )
        arg = compose_args_for_converse_api(
            [message],
            MODEL,
            guardrail=self.guardrail,
            stream=False,
        )

        pprint(arg)

        response = call_converse_api(arg)
        pprint(response)


if __name__ == "__main__":
    unittest.main()
