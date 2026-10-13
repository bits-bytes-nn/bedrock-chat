import unittest
from unittest.mock import patch

from app import main
from app.user import User
from fastapi import HTTPException
from fastapi.testclient import TestClient


class TestAuthMiddleware(unittest.TestCase):
    client = TestClient(main.app)

    def test_rejected_token_returns_403(self):
        rejected = HTTPException(
            status_code=403, detail="Could not validate credentials"
        )
        with patch.object(main, "user_from_token", side_effect=rejected):
            response = self.client.get(
                "/conversations", headers={"Authorization": "Bearer access-token"}
            )
        self.assertEqual(response.status_code, 403)

    def test_route_checks_reuse_the_verified_user(self):
        user = User(id="u", name="u", email="u@example.com", groups=[])
        with patch.object(main, "user_from_token", return_value=user) as verify:
            response = self.client.get(
                "/admin/public-bots", headers={"Authorization": "Bearer id-token"}
            )
        self.assertEqual(response.status_code, 403)
        verify.assert_called_once_with("id-token")

    def test_malformed_header_returns_403(self):
        response = self.client.get(
            "/conversations",
            headers={"Authorization": "token", "Origin": "https://example.com"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("access-control-allow-origin", response.headers)


class TestUnhandledErrors(unittest.TestCase):
    client = TestClient(main.app)

    def test_returns_500_and_keeps_serving(self):
        with patch(
            "app.routes.conversation.fetch_conversation",
            side_effect=RuntimeError("arn:aws:iam::123456789012:role/x"),
        ):
            response = self.client.get(
                "/conversation/c", headers={"Origin": "https://example.com"}
            )

        self.assertEqual(response.status_code, 500)
        self.assertNotIn("arn:aws", response.text)
        self.assertIn("access-control-allow-origin", response.headers)
        self.assertEqual(self.client.get("/health").status_code, 200)


class TestErrorCodes(unittest.TestCase):
    def test_coded_errors_carry_their_code_and_params(self):
        from app.repositories.common import LimitExceededError

        handler = main.error_handler_factory(400)
        response = handler(None, LimitExceededError("too many", "a_limit", limit=2))  # type: ignore[arg-type]
        import json

        self.assertEqual(
            json.loads(response.body),
            {"errors": ["too many"], "code": "a_limit", "params": {"limit": 2}},
        )

    def test_other_errors_keep_the_plain_body(self):
        import json

        response = main.error_handler_factory(400)(None, ValueError("bad"))  # type: ignore[arg-type]
        self.assertEqual(json.loads(response.body), {"errors": ["bad"]})


if __name__ == "__main__":
    unittest.main()
