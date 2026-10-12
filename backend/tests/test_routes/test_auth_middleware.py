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
        response = self.client.get("/conversations", headers={"Authorization": "token"})
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
