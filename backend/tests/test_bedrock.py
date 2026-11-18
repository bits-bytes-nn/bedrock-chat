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


class TestFilterAvailableModels(unittest.TestCase):
    PROFILES = TestGetModelId.PROFILES

    def available(self, models, on_demand=frozenset(), **kwargs) -> list[str]:
        # Explicit, because app.bedrock reads the defaults when another test module
        # imported it first.
        kwargs.setdefault("enable_global", True)
        kwargs.setdefault("enable_cross_region", True)
        with (
            patch.object(
                bedrock, "_list_system_inference_profiles", return_value=self.PROFILES
            ),
            patch.object(bedrock, "_list_on_demand_models", return_value=on_demand),
        ):
            return bedrock.filter_available_models(
                models, bedrock_region="ap-northeast-2", **kwargs
            )

    def test_offered_through_an_inference_profile(self):
        self.assertEqual(
            self.available(["claude-v4.6-sonnet", "amazon-nova-pro"]),
            ["claude-v4.6-sonnet", "amazon-nova-pro"],
        )

    def test_offered_on_demand_in_the_region(self):
        self.assertEqual(
            self.available(
                ["gpt-oss-20b"],
                on_demand=frozenset({"openai.gpt-oss-20b-1:0"}),
            ),
            ["gpt-oss-20b"],
        )

    def test_drops_models_without_a_profile_or_on_demand_throughput(self):
        # The profile named after mistral-large routes to another model.
        self.assertEqual(
            self.available(["mistral-large", "gpt-oss-120b", "amazon-nova-pro"]),
            ["amazon-nova-pro"],
        )

    def test_profiles_count_only_when_enabled(self):
        with (
            patch.object(bedrock, "_list_system_inference_profiles") as profiles,
            patch.object(bedrock, "_list_on_demand_models", return_value=frozenset()),
        ):
            models = bedrock.filter_available_models(
                ["claude-v4.6-sonnet"], enable_global=False, enable_cross_region=False
            )
        self.assertEqual(models, [])
        profiles.assert_not_called()

    def test_drops_retired_and_unknown_models(self):
        self.assertEqual(self.available(["claude-v3.7-sonnet", "no-such-model"]), [])

    def failing_lookup(self, failing: str):
        error = ClientError(
            {"Error": {"Code": "ThrottlingException", "Message": ""}}, "List"
        )
        return (
            patch.object(
                bedrock,
                "_list_system_inference_profiles",
                **(
                    {"side_effect": error}
                    if failing == "profiles"
                    else {"return_value": {}}
                ),
            ),
            patch.object(
                bedrock,
                "_list_on_demand_models",
                **(
                    {"side_effect": error}
                    if failing == "on_demand"
                    else {"return_value": frozenset()}
                ),
            ),
        )

    def test_a_failed_lookup_keeps_every_model(self):
        models = ["gpt-oss-120b", "mistral-large"]
        for failing in ("profiles", "on_demand"):
            bedrock._lookup_failed_at.clear()
            profiles, on_demand = self.failing_lookup(failing)
            with profiles, on_demand:
                self.assertEqual(
                    bedrock.filter_available_models(
                        models, enable_global=True, enable_cross_region=True
                    ),
                    models,
                )

    def test_a_slow_lookup_counts_as_failed(self):
        with (
            patch.object(
                bedrock, "_list_system_inference_profiles", side_effect=TimeoutError
            ),
            patch.object(bedrock, "_list_on_demand_models", return_value=frozenset()),
        ):
            self.assertEqual(
                bedrock.filter_available_models(
                    ["gpt-oss-120b"], enable_global=True, enable_cross_region=True
                ),
                ["gpt-oss-120b"],
            )


class TestLookupFailures(unittest.TestCase):
    ERROR = ClientError(
        {"Error": {"Code": "ThrottlingException", "Message": ""}}, "List"
    )

    def test_a_failed_lookup_is_not_repeated_for_a_while(self):
        lookup = MagicMock(side_effect=self.ERROR)
        with patch.object(
            bedrock.time, "monotonic", side_effect=[100.0, 130.0, 200.0, 200.0]
        ):
            for _ in range(3):
                with self.assertRaises(bedrock.ModelLookupUnavailable):
                    bedrock._lookup(lookup, "r")
        # Called at 100 s, skipped at 130 s, called again at 200 s.
        self.assertEqual(lookup.call_count, 2)

    def test_failures_are_remembered_per_region(self):
        with self.assertRaises(bedrock.ModelLookupUnavailable):
            bedrock._lookup(MagicMock(side_effect=self.ERROR), "a")
        self.assertEqual(bedrock._lookup(MagicMock(return_value=1), "b"), 1)

    def test_get_model_id_skips_a_lookup_that_failed_recently(self):
        with patch.object(
            bedrock, "_list_system_inference_profiles", side_effect=self.ERROR
        ) as profiles:
            for _ in range(2):
                self.assertEqual(
                    get_model_id(
                        MODEL,
                        enable_global=True,
                        enable_cross_region=True,
                        bedrock_region="us-east-1",
                    ),
                    "global.anthropic.claude-haiku-5-5",
                )
        profiles.assert_called_once()

    def test_the_client_does_not_retry(self):
        with patch.object(bedrock.boto3, "client") as client:
            bedrock._bedrock_client("r")
        config = client.call_args.kwargs["config"]
        self.assertEqual(config.retries["max_attempts"], 1)


class TestListInferenceProfilesDeadline(unittest.TestCase):
    def test_stops_paging_after_the_deadline(self):
        client = MagicMock()
        client.list_inference_profiles.return_value = {
            "inferenceProfileSummaries": [],
            "nextToken": "t",
        }
        bedrock._list_system_inference_profiles.cache_clear()
        with (
            patch.object(bedrock.boto3, "client", return_value=client),
            patch.object(bedrock.time, "monotonic", side_effect=[0.0, 5.0, 11.0]),
        ):
            with self.assertRaises(TimeoutError):
                bedrock._list_system_inference_profiles("test-region")
        bedrock._list_system_inference_profiles.cache_clear()
        self.assertEqual(client.list_inference_profiles.call_count, 2)


class TestListOnDemandModels(unittest.TestCase):
    def test_lists_on_demand_model_ids(self):
        client = MagicMock()
        client.list_foundation_models.return_value = {
            "modelSummaries": [{"modelId": "a"}, {"modelId": "b"}]
        }
        bedrock._list_on_demand_models.cache_clear()
        with patch.object(bedrock.boto3, "client", return_value=client):
            models = bedrock._list_on_demand_models("test-region")
        bedrock._list_on_demand_models.cache_clear()

        self.assertEqual(models, frozenset({"a", "b"}))
        client.list_foundation_models.assert_called_once_with(
            byInferenceType="ON_DEMAND"
        )


if __name__ == "__main__":
    unittest.main()
