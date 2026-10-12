import unittest
from unittest.mock import patch

from app import main
from fastapi import HTTPException
from fastapi.testclient import TestClient


class TestAuthMiddleware(unittest.TestCase):
    client = TestClient(main.app)

    def test_rejected_token_returns_403(self):
        rejected = HTTPException(
            status_code=403, detail="Could not validate credentials"
        )
        with patch.object(main, "get_current_user", side_effect=rejected):
            response = self.client.get(
                "/conversations", headers={"Authorization": "Bearer access-token"}
            )
        self.assertEqual(response.status_code, 403)

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


if __name__ == "__main__":
    unittest.main()
