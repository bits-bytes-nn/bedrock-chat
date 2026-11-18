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

    def test_frontend_capabilities_match_registry(self):
        # The UI forces the reasoning toggle and refuses PDF and Office files from
        # these flags, so they must follow the request rules of the backend.
        use_model = (FRONTEND / "hooks" / "useModel.ts").read_text()
        models_block = use_model[use_model.index("const MODELS") :]
        models_block = models_block[: models_block.index("\n];")]
        entries = dict(
            re.findall(r"modelId: '([^']+)',(.*?)(?=modelId:|\Z)", models_block, re.S)
        )
        self.assertEqual(set(entries), set(MODELS))
        for model, spec in MODELS.items():
            with self.subTest(model=model):
                self.assertEqual(
                    "ALWAYS_REASONING" in entries[model], spec.reasoning == "always"
                )
                self.assertEqual(
                    "supportDocument: false" in entries[model],
                    not spec.supports_documents,
                )

    def test_frontend_offers_every_search_engine(self):
        from app.routes.schemas.bot import type_search_engine

        tools = (
            FRONTEND / "features" / "agent" / "components" / "AvailableTools.tsx"
        ).read_text()
        block = re.search(r"SEARCH_ENGINES: SearchEngine\[\] = \[(.*?)\]", tools, re.S)
        assert block is not None
        offered = re.findall(r"'([^']+)'", block.group(1))
        self.assertEqual(sorted(offered), sorted(get_args(type_search_engine)))

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

    def test_falls_back_to_default_stop_sequences(self):
        config = generation_params_to_converse_configuration(
            "mistral-large", generation_params(stop_sequences=[])
        )

        self.assertEqual(
            config["inferenceConfig"]["stopSequences"], ["[INST]", "[/INST]"]
        )
        self.assertNotIn("additionalModelRequestFields", config)

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

    def test_uses_input_price_when_cache_prices_are_missing(self):
        price = calculate_price("gpt-oss-120b", 1000, 1000, 1000, 1000)

        self.assertAlmostEqual(price, 0.0003 + 0.0006 + 0.0003 + 0.0003)


if __name__ == "__main__":
    unittest.main()
