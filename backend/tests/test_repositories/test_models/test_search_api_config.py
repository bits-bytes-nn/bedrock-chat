import unittest
from uuid import uuid4

import pytest
from app.repositories.models.custom_bot import InternetToolModel, SearchApiConfigModel
from app.routes.schemas.bot import InternetTool, SearchApiConfig
from moto import mock_aws
from pydantic import ValidationError

API_KEY = "test-api-key"


@mock_aws
class TestSearchApiConfigModel(unittest.TestCase):
    def test_lifecycle(self):
        # Create the model from input
        bot_id = str(uuid4())
        input_config = SearchApiConfig(api_key=API_KEY, max_results=15)
        model = SearchApiConfigModel.from_search_api_config(
            input_config, "tavily", "user123", bot_id
        )

        # The key is stored under the engine's prefix.
        self.assertIn(f":secret:tavily/user123/{bot_id}", model.secret_arn)
        self.assertEqual(model.api_key, API_KEY)
        self.assertEqual(model.max_results, 15)

        serialized = model.model_dump()
        # API key should be empty
        self.assertEqual(serialized["api_key"], "")
        deserialized = SearchApiConfigModel.model_validate(serialized)

        # API key should be loaded from Secrets Manager
        self.assertEqual(deserialized.api_key, API_KEY)
        self.assertEqual(deserialized.secret_arn, model.secret_arn)
        self.assertEqual(deserialized.max_results, 15)

    def test_reads_the_firecrawl_config_of_older_items(self):
        model = SearchApiConfigModel.from_search_api_config(
            SearchApiConfig(api_key=API_KEY, max_results=7), "firecrawl", "u", "b"
        )
        tool = InternetToolModel.model_validate(
            {
                "tool_type": "internet",
                "name": "internet_search",
                "description": "",
                "search_engine": "firecrawl",
                "firecrawl_config": model.model_dump(),
            }
        )

        assert tool.search_api_config is not None
        self.assertEqual(tool.search_api_config.api_key, API_KEY)
        self.assertEqual(tool.search_api_config.max_results, 7)
        self.assertNotIn("firecrawl_config", tool.model_dump())

    def test_missing_secret_is_not_a_validation_error(self):
        # A ValueError would reach the client as a 422 that names the secret ARN.
        with self.assertRaises(RuntimeError):
            SearchApiConfigModel.model_validate(
                {
                    "secret_arn": "arn:aws:secretsmanager:us-east-1:123456789012:secret:x",
                    "api_key": "",
                }
            )


def internet_tool(engine: str, config: dict | None) -> InternetTool:
    return InternetTool.model_validate(
        {
            "toolType": "internet",
            "name": "internet_search",
            "description": "",
            "searchEngine": engine,
            "searchApiConfig": config,
        }
    )


@pytest.mark.parametrize("engine", ["firecrawl", "tavily", "brave"])
def test_engines_with_an_api_key_require_it(engine):
    with pytest.raises(ValidationError, match="API key is required"):
        internet_tool(engine, None)
    with pytest.raises(ValidationError, match="API key is empty"):
        internet_tool(engine, {"apiKey": "", "maxResults": 5})


@pytest.mark.parametrize(
    "engine, max_results", [("firecrawl", 100), ("tavily", 20), ("brave", 20)]
)
def test_max_results_is_limited_per_engine(engine, max_results):
    internet_tool(engine, {"apiKey": API_KEY, "maxResults": max_results})
    # Firecrawl reaches the limit of the field itself.
    with pytest.raises(
        ValidationError, match=f"(at most|less than or equal to) {max_results}"
    ):
        internet_tool(engine, {"apiKey": API_KEY, "maxResults": max_results + 1})


def test_duckduckgo_needs_no_api_key():
    assert internet_tool("duckduckgo", None).search_api_config is None


if __name__ == "__main__":
    unittest.main()
