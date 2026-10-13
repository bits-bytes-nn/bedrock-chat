import unittest

from app.routes.schemas.conversation import FeedbackInput
from pydantic import ValidationError


class TestFeedbackInput(unittest.TestCase):
    def test_reads_the_camel_case_request(self):
        self.assertTrue(FeedbackInput.model_validate({"thumbsUp": True}).thumbs_up)

    def test_requires_a_category_for_negative_feedback(self):
        with self.assertRaises(ValidationError):
            FeedbackInput.model_validate({"thumbsUp": False})
        feedback = FeedbackInput.model_validate({"thumbsUp": False, "category": "x"})
        self.assertEqual(feedback.category, "x")
