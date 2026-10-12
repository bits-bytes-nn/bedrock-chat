import sys

sys.path.insert(0, ".")
import unittest
from unittest.mock import patch

from app.usecases import global_config
from app.usecases.global_config import (
    get_default_model,
    get_global_available_models,
    get_title_model,
)


class TestGetGlobalAvailableModels(unittest.TestCase):
    """Test cases for get_global_available_models function."""

    @patch.object(global_config, "GLOBAL_AVAILABLE_MODELS", None)
    def test_no_environment_variable_returns_empty_list(self):
        """Test that when no GLOBAL_AVAILABLE_MODELS env var is set, empty list is returned."""
        result = get_global_available_models()
        self.assertEqual(result, [])

    @patch.object(global_config, "GLOBAL_AVAILABLE_MODELS", "")
    def test_empty_environment_variable_returns_empty_list(self):
        """Test that when GLOBAL_AVAILABLE_MODELS is empty string, empty list is returned."""
        result = get_global_available_models()
        self.assertEqual(result, [])

    @patch.object(global_config, "GLOBAL_AVAILABLE_MODELS", "[]")
    def test_empty_json_array_returns_empty_list(self):
        """Test that empty JSON array returns empty list."""
        result = get_global_available_models()
        self.assertEqual(result, [])

    @patch.object(
        global_config,
        "GLOBAL_AVAILABLE_MODELS",
        '["claude-v5-sonnet", "claude-v4.6-sonnet", "amazon-nova-pro"]',
    )
    def test_valid_json_array_returns_models(self):
        """Test that valid JSON array returns the list of models."""
        result = get_global_available_models()
        self.assertEqual(
            result, ["claude-v5-sonnet", "claude-v4.6-sonnet", "amazon-nova-pro"]
        )

    @patch.object(global_config, "GLOBAL_AVAILABLE_MODELS", "invalid json")
    def test_invalid_json_raises(self):
        """A broken allowlist must not allow every model."""
        with self.assertRaises(ValueError):
            get_global_available_models()

    def test_non_array_json_raises(self):
        """JSON values other than an array are rejected."""
        for value in ['{"not": "an array"}', '"string instead of array"', "true"]:
            with patch.object(global_config, "GLOBAL_AVAILABLE_MODELS", value):
                with self.assertRaises(ValueError):
                    get_global_available_models()

    @patch.object(global_config, "GLOBAL_AVAILABLE_MODELS", '[""]')
    def test_empty_string_models_filtered_out(self):
        """Test that empty string models are filtered out from the array."""
        result = get_global_available_models()
        self.assertEqual(result, [])

    @patch.object(global_config, "GLOBAL_AVAILABLE_MODELS", '[null, "valid-model"]')
    def test_null_values_filtered_out(self):
        """Test that null values are filtered out from the array."""
        result = get_global_available_models()
        self.assertEqual(result, ["valid-model"])

    @patch.object(
        global_config, "GLOBAL_AVAILABLE_MODELS", '["model1", "", null, "model2", ""]'
    )
    def test_mixed_valid_and_invalid_values_filtered(self):
        """Test that empty strings and null values are filtered out, keeping only valid models."""
        result = get_global_available_models()
        self.assertEqual(result, ["model1", "model2"])


class TestGetDefaultModel(unittest.TestCase):
    """Test cases for get_default_model function."""

    @patch.object(global_config, "DEFAULT_MODEL", "claude-v4.6-sonnet")
    def test_returns_configured_model(self):
        """Test that configured DEFAULT_MODEL is returned."""
        from app.usecases.global_config import get_default_model

        result = get_default_model()
        self.assertEqual(result, "claude-v4.6-sonnet")

    @patch.object(global_config, "DEFAULT_MODEL", None)
    def test_falls_back_to_default_when_none(self):
        """Test that default model is returned when DEFAULT_MODEL is None."""
        from app.usecases.global_config import get_default_model

        result = get_default_model()
        self.assertEqual(result, "claude-v5.5-sonnet")

    @patch.object(global_config, "DEFAULT_MODEL", "")
    def test_falls_back_to_default_when_empty_string(self):
        """Test that default model is returned when DEFAULT_MODEL is empty string."""
        from app.usecases.global_config import get_default_model

        result = get_default_model()
        self.assertEqual(result, "claude-v5.5-sonnet")

    @patch.object(global_config, "DEFAULT_MODEL", "   ")
    def test_falls_back_to_default_when_whitespace(self):
        """Test that default model is returned when DEFAULT_MODEL contains only whitespace."""
        from app.usecases.global_config import get_default_model

        result = get_default_model()
        self.assertEqual(result, "claude-v5.5-sonnet")

    @patch.object(global_config, "DEFAULT_MODEL", "  amazon-nova-pro  ")
    def test_strips_whitespace_from_configured_model(self):
        """Test that whitespace is stripped from configured model."""
        from app.usecases.global_config import get_default_model

        result = get_default_model()
        self.assertEqual(result, "amazon-nova-pro")


class TestRetiredConfiguredModels(unittest.TestCase):
    @patch.object(global_config, "DEFAULT_MODEL", "claude-v3.7-sonnet")
    def test_default_model_ignores_retired_model(self):
        self.assertEqual(get_default_model(), "claude-v5.5-sonnet")

    @patch.object(global_config, "TITLE_MODEL", "claude-v3-haiku")
    @patch.object(global_config, "DEFAULT_MODEL", "claude-v4.6-sonnet")
    def test_title_model_skips_retired_model(self):
        self.assertEqual(get_title_model(), "claude-v4.6-sonnet")


class TestGetTitleModel(unittest.TestCase):
    """Test cases for get_title_model function."""

    @patch.object(global_config, "TITLE_MODEL", "claude-v4.5-haiku")
    @patch.object(global_config, "DEFAULT_MODEL", "claude-v5-sonnet")
    def test_returns_title_model_when_set(self):
        """Test that TITLE_MODEL is returned when configured."""
        from app.usecases.global_config import get_title_model

        result = get_title_model()
        self.assertEqual(result, "claude-v4.5-haiku")

    @patch.object(global_config, "TITLE_MODEL", None)
    @patch.object(global_config, "DEFAULT_MODEL", "claude-v4.6-sonnet")
    def test_falls_back_to_default_model_when_title_model_none(self):
        """Test that DEFAULT_MODEL is returned when TITLE_MODEL is None."""
        from app.usecases.global_config import get_title_model

        result = get_title_model()
        self.assertEqual(result, "claude-v4.6-sonnet")

    @patch.object(global_config, "TITLE_MODEL", "")
    @patch.object(global_config, "DEFAULT_MODEL", "amazon-nova-lite")
    def test_falls_back_to_default_model_when_title_model_empty(self):
        """Test that DEFAULT_MODEL is returned when TITLE_MODEL is empty string."""
        from app.usecases.global_config import get_title_model

        result = get_title_model()
        self.assertEqual(result, "amazon-nova-lite")

    @patch.object(global_config, "TITLE_MODEL", None)
    @patch.object(global_config, "DEFAULT_MODEL", None)
    def test_falls_back_to_haiku_when_both_none(self):
        """Test that claude-v5.5-haiku is returned when both TITLE_MODEL and DEFAULT_MODEL are None."""
        from app.usecases.global_config import get_title_model

        result = get_title_model()
        self.assertEqual(result, "claude-v5.5-haiku")

    @patch.object(global_config, "TITLE_MODEL", "")
    @patch.object(global_config, "DEFAULT_MODEL", "")
    def test_falls_back_to_haiku_when_both_empty(self):
        """Test that claude-v5.5-haiku is returned when both TITLE_MODEL and DEFAULT_MODEL are empty."""
        from app.usecases.global_config import get_title_model

        result = get_title_model()
        self.assertEqual(result, "claude-v5.5-haiku")

    @patch.object(global_config, "TITLE_MODEL", "   ")
    @patch.object(global_config, "DEFAULT_MODEL", "   ")
    def test_falls_back_to_haiku_when_both_whitespace(self):
        """Test that claude-v5.5-haiku is returned when both contain only whitespace."""
        from app.usecases.global_config import get_title_model

        result = get_title_model()
        self.assertEqual(result, "claude-v5.5-haiku")

    @patch.object(global_config, "TITLE_MODEL", "  mistral-large  ")
    @patch.object(global_config, "DEFAULT_MODEL", "claude-v5-sonnet")
    def test_strips_whitespace_from_title_model(self):
        """Test that whitespace is stripped from TITLE_MODEL."""
        from app.usecases.global_config import get_title_model

        result = get_title_model()
        self.assertEqual(result, "mistral-large")

    @patch.object(global_config, "TITLE_MODEL", "")
    @patch.object(global_config, "DEFAULT_MODEL", "  llama3-3-70b-instruct  ")
    def test_strips_whitespace_from_default_model_fallback(self):
        """Test that whitespace is stripped from DEFAULT_MODEL when used as fallback."""
        from app.usecases.global_config import get_title_model

        result = get_title_model()
        self.assertEqual(result, "llama3-3-70b-instruct")
