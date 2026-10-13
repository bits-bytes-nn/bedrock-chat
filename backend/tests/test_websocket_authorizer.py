import unittest
from unittest.mock import patch

import requests
from app import websocket_authorizer
from jwt import InvalidTokenError

ARN = "arn:aws:execute-api:us-east-1:123456789012:api/dev/$connect"


def authorize(query: dict | None) -> dict:
    return websocket_authorizer.handler(
        {"methodArn": ARN, "queryStringParameters": query}, None
    )


class TestWebSocketAuthorizer(unittest.TestCase):
    def effect(self, response: dict) -> str:
        return response["policyDocument"]["Statement"][0]["Effect"]

    def test_allows_a_valid_id_token(self):
        with patch.object(
            websocket_authorizer, "verify_token", return_value={"sub": "user"}
        ) as verify:
            response = authorize({"token": "id-token"})
        verify.assert_called_once_with("id-token")
        self.assertEqual(self.effect(response), "Allow")
        self.assertEqual(response["principalId"], "user")

    def test_denies_invalid_or_missing_tokens(self):
        with patch.object(
            websocket_authorizer, "verify_token", side_effect=InvalidTokenError()
        ):
            for query in ({"token": "bad"}, {}, None):
                self.assertEqual(self.effect(authorize(query)), "Deny")

    def test_logs_signing_key_fetch_failures_as_errors(self):
        with patch.object(
            websocket_authorizer,
            "verify_token",
            side_effect=requests.ConnectionError("secret-token-in-url"),
        ), self.assertLogs(websocket_authorizer.logger, "WARNING") as logs:
            response = authorize({"token": "id-token"})
        self.assertEqual(self.effect(response), "Deny")
        self.assertEqual([r.levelname for r in logs.records], ["ERROR"])
        self.assertIn("Failed to fetch the signing keys", logs.output[0])
        self.assertNotIn("secret-token-in-url", logs.output[0])
        self.assertNotIn("id-token", logs.output[0])

    def test_logs_invalid_tokens_as_warnings(self):
        with patch.object(
            websocket_authorizer, "verify_token", side_effect=InvalidTokenError()
        ), self.assertLogs(websocket_authorizer.logger, "WARNING") as logs:
            authorize({"token": "bad"})
        self.assertEqual([r.levelname for r in logs.records], ["WARNING"])
