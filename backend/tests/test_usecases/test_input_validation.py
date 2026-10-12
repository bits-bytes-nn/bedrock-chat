import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, ".")

from app.repositories.common import RecordNotFoundError
from app.repositories.models.conversation import AttachmentContentModel
from app.repositories.usage_analysis import _to_datehour_range, _validate_query
from app.usecases import bot as bot_usecase
from app.usecases.bot import issue_presigned_url, validate_new_bot_id
from app.user import User

BOT_ID = "01J9Z3Q4R5S6T7V8W9X0Y1Z2A3"


class TestValidateNewBotId(unittest.TestCase):
    def test_accepts_unused_ulid(self):
        with patch.object(
            bot_usecase, "find_bot_by_id", side_effect=RecordNotFoundError("none")
        ):
            validate_new_bot_id(BOT_ID)

    def test_rejects_used_id(self):
        with patch.object(bot_usecase, "find_bot_by_id", return_value=MagicMock()):
            with self.assertRaises(ValueError):
                validate_new_bot_id(BOT_ID)

    def test_rejects_non_ulid(self):
        with self.assertRaises(ValueError):
            validate_new_bot_id("../other-user/bot")


class TestIssuePresignedUrl(unittest.TestCase):
    user = User(id="user", name="user", email="user@example.com", groups=[])

    def issue(self, bot_id: str = BOT_ID, filename: str = "doc.pdf") -> str:
        return issue_presigned_url(self.user, bot_id, filename, "application/pdf")

    def test_allows_uploads_for_a_new_bot(self):
        with patch.object(
            bot_usecase, "find_bot_by_id", side_effect=RecordNotFoundError("none")
        ), patch.object(bot_usecase, "generate_presigned_url", return_value="url"):
            self.assertEqual(self.issue(), "url")

    def test_rejects_another_users_bot(self):
        bot = MagicMock()
        bot.is_editable_by_user.return_value = False
        with patch.object(bot_usecase, "find_bot_by_id", return_value=bot):
            with self.assertRaises(PermissionError):
                self.issue()

    def test_rejects_invalid_keys(self):
        for bot_id, filename in (("../bot", "doc.pdf"), (BOT_ID, "a/b.pdf")):
            with self.assertRaises(ValueError):
                self.issue(bot_id, filename)


class TestAttachmentName(unittest.TestCase):
    def name(self, file_name: str) -> str:
        return AttachmentContentModel(
            content_type="attachment", body=b"x", file_name=file_name
        ).format_and_name[1]

    def test_keeps_valid_names(self):
        self.assertEqual(self.name("report (1).pdf"), "report (1)")

    def test_names_without_valid_characters_are_not_empty_or_equal(self):
        korean, japanese = self.name("보고서.pdf"), self.name("報告書.pdf")
        self.assertRegex(korean, r"^[0-9a-f]{8}$")
        self.assertNotEqual(korean, japanese)


class TestToDatehourRange(unittest.TestCase):
    def test_converts_bounds(self):
        self.assertEqual(
            _to_datehour_range("2026101100", "2026101123"),
            ("2026/10/11/00", "2026/10/11/23"),
        )

    def test_rejects_injection(self):
        with self.assertRaises(ValueError):
            _to_datehour_range("2026101100' OR '1'='1", "2026101123")


class TestValidateQuery(unittest.TestCase):
    def test_rejects_out_of_range_limit(self):
        for limit in (0, 1001):
            with self.assertRaises(ValueError):
                _validate_query(limit, None, None)

    def test_rejects_half_open_period(self):
        with self.assertRaises(ValueError):
            _validate_query(10, "2026101100", None)


if __name__ == "__main__":
    unittest.main()
