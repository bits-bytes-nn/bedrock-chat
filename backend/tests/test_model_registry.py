import re
import sys
import unittest
from pathlib import Path
from typing import get_args

sys.path.insert(0, ".")

from app.bedrock import calculate_price, generation_params_to_converse_configuration
from app.model_registry import MODELS, RETIRED_MODELS
from app.repositories.models.custom_bot import GenerationParamsModel
from app.routes.schemas.conversation import type_model_name

FRONTEND = Path(__file__).resolve().parents[2] / "frontend" / "src"


def generation_params(**overrides) -> GenerationParamsModel:
    params = dict(
        max_tokens=2000,
        top_k=250,
        top_p=0.999,
        temperature=1.0,
        stop_sequences=["STOP"],
        reasoning_params={"budget_tokens": 1024},
    )
    params.update(overrides)
    return GenerationParamsModel.model_validate(params)


class TestRegistryConsistency(unittest.TestCase):
    def test_model_names_match_registry(self):
        self.assertEqual(set(get_args(type_model_name)), set(MODELS) | RETIRED_MODELS)
        self.assertFalse(set(MODELS) & RETIRED_MODELS)

    def test_frontend_offers_exactly_the_available_models(self):
        constants = (FRONTEND / "constants" / "index.ts").read_text()
        keys_block = re.search(
            r"AVAILABLE_MODEL_KEYS = \[(.*?)\] as const", constants, re.S
        )
        assert keys_block is not None
        frontend_keys = set(re.findall(r"'([^']+)'", keys_block.group(1)))

        use_model = (FRONTEND / "hooks" / "useModel.ts").read_text()
        ui_models = set(re.findall(r"modelId: '([^']+)'", use_model))

        self.assertEqual(frontend_keys, set(MODELS))
        self.assertEqual(ui_models, set(MODELS))

    def test_frontend_has_english_labels(self):
        english = (FRONTEND / "i18n" / "en" / "index.ts").read_text()
        missing = [model for model in MODELS if f"'{model}': {{" not in english]
        self.assertEqual(missing, [])


class TestGenerationParamsToConverseConfiguration(unittest.TestCase):
    def test_modern_claude_omits_sampling_parameters(self):
        config = generation_params_to_converse_configuration(
            "claude-v5.5-sonnet", generation_params()
        )

        self.assertEqual(
            config["inferenceConfig"], {"maxTokens": 2000, "stopSequences": ["STOP"]}
        )
        self.assertNotIn("additionalModelRequestFields", config)

    def test_modern_claude_uses_adaptive_thinking(self):
        config = generation_params_to_converse_configuration(
            "claude-v5.5-opus", generation_params(), enable_reasoning=True
        )

        self.assertEqual(
            config["additionalModelRequestFields"], {"thinking": {"type": "adaptive"}}
        )

    def test_budget_thinking_raises_max_tokens_above_budget(self):
        config = generation_params_to_converse_configuration(
            "claude-v4.5-sonnet",
            generation_params(max_tokens=1000),
            enable_reasoning=True,
        )

        self.assertEqual(config["inferenceConfig"]["maxTokens"], 2048)
        self.assertEqual(config["inferenceConfig"]["temperature"], 1.0)
        self.assertEqual(
            config["additionalModelRequestFields"],
            {"thinking": {"type": "enabled", "budget_tokens": 1024}},
        )

    def test_claude_sends_only_one_of_temperature_and_top_p(self):
        config = generation_params_to_converse_configuration(
            "claude-v4.5-haiku", generation_params(temperature=0.3)
        )

        self.assertEqual(config["inferenceConfig"]["temperature"], 0.3)
        self.assertNotIn("topP", config["inferenceConfig"])
        self.assertEqual(config["additionalModelRequestFields"], {"top_k": 250})

    def test_gpt_sends_only_max_tokens(self):
        config = generation_params_to_converse_configuration(
            "gpt-6-sol", generation_params()
        )

        self.assertEqual(config["inferenceConfig"], {"maxTokens": 2000})

    def test_nova_caps_top_k(self):
        config = generation_params_to_converse_configuration(
            "amazon-nova-pro", generation_params(top_k=500)
        )

        self.assertEqual(
            config["additionalModelRequestFields"], {"inferenceConfig": {"topK": 128}}
        )

    def test_uses_model_default_max_tokens_without_params(self):
        config = generation_params_to_converse_configuration("claude-v5.5-haiku")

        self.assertEqual(
            config["inferenceConfig"]["maxTokens"],
            MODELS["claude-v5.5-haiku"].default_max_tokens,
        )


class TestCalculatePrice(unittest.TestCase):
    def test_calculates_price_per_thousand_tokens(self):
        price = calculate_price("claude-v5.5-sonnet", 1000, 1000, 1000, 1000)

        self.assertAlmostEqual(price, 0.002 + 0.01 + 0.0001 + 0.0025)

    def test_returns_zero_without_price(self):
        self.assertEqual(calculate_price("gpt-6-sol", 1000, 1000, 0, 0), 0.0)


if __name__ == "__main__":
    unittest.main()
