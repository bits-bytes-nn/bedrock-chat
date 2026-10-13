"""cdk/custom-resources/cognito-trigger/index.py runs on every deployment that sets
autoJoinUserGroups, so it must keep the rest of the user pool configuration."""

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

HANDLER = (
    Path(__file__).resolve().parents[2]
    / "cdk/custom-resources/cognito-trigger/index.py"
)


def load_handler(cognito: MagicMock):
    cfnresponse = types.SimpleNamespace(
        SUCCESS="SUCCESS", FAILED="FAILED", send=MagicMock()
    )
    spec = importlib.util.spec_from_file_location("cognito_trigger", HANDLER)
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    with patch.dict(sys.modules, {"cfnresponse": cfnresponse}), patch.dict(
        "os.environ", {"USER_POOL_ID": "pool"}
    ), patch("boto3.client", return_value=cognito):
        spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module, cfnresponse


class TestCognitoTriggerResource(unittest.TestCase):
    def test_update_replaces_only_its_triggers(self):
        cognito = MagicMock()
        cognito.describe_user_pool.return_value = {
            "UserPool": {
                "LambdaConfig": {
                    "PreSignUp": "check-email-domain",
                    "PostConfirmation": "old",
                    "PostAuthentication": "old",
                },
                "AdminCreateUserConfig": {"AllowAdminCreateUserOnly": True},
                "UserAttributeUpdateSettings": {
                    "AttributesRequireVerificationBeforeUpdate": ["email"]
                },
                "UserPoolTier": "ESSENTIALS",
                "Id": "pool",
            }
        }
        module, cfnresponse = load_handler(cognito)
        triggers = {"PostConfirmation": "new", "PostAuthentication": "new"}

        module.handler(
            {
                "RequestType": "Update",
                "PhysicalResourceId": "pool-triggers",
                "ResourceProperties": {"Triggers": triggers},
                "OldResourceProperties": {"Triggers": triggers},
            },
            None,
        )

        update = cognito.update_user_pool.call_args.kwargs
        self.assertEqual(
            update["LambdaConfig"],
            {"PreSignUp": "check-email-domain", **triggers},
        )
        # Self sign-up stays off, and the other settings are sent back unchanged.
        self.assertEqual(
            update["AdminCreateUserConfig"], {"AllowAdminCreateUserOnly": True}
        )
        self.assertIn("UserAttributeUpdateSettings", update)
        self.assertEqual(update["UserPoolTier"], "ESSENTIALS")
        self.assertNotIn("Id", update)
        self.assertEqual(cfnresponse.send.call_args.args[2], "SUCCESS")
