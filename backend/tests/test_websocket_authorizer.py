import unittest
from unittest.mock import patch

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
