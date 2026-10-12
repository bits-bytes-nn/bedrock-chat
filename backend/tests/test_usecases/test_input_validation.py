import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, ".")

from app.repositories.common import RecordNotFoundError
from app.repositories.usage_analysis import _to_datehour_range, _validate_query
from app.usecases import bot as bot_usecase
from app.usecases.bot import validate_new_bot_id

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
