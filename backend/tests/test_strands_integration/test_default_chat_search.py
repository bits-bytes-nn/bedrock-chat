"""The internet search of chats without a bot, which the deployment configures."""

from unittest.mock import patch

import pytest
from app.strands_integration import utils
from app.strands_integration.tools import internet_search
from app.usecases import global_config

SECRET_ARN = "arn:aws:secretsmanager:us-east-1:123456789012:secret:key"


def configure(engine: str, secret_arn: str = ""):
    return patch.multiple(
        global_config,
        DEFAULT_CHAT_SEARCH_ENGINE=engine,
        DEFAULT_CHAT_SEARCH_API_KEY_SECRET_ARN=secret_arn,
    )


def tool_names(model: str = "claude-v5.5-haiku") -> list[str]:
    return [tool.tool_name for tool in utils.get_strands_tools(None, model)]


def test_chats_without_a_bot_have_no_tools_by_default():
    with configure(""):
        assert tool_names() == []


def test_chats_without_a_bot_get_the_internet_search_of_the_deployment():
    with configure("duckduckgo"):
        assert tool_names() == ["internet_search"]


def test_models_without_tool_use_get_no_search():
    with configure("duckduckgo"), patch.object(
        utils, "is_tooluse_supported", return_value=False
    ):
        assert tool_names() == []


def test_an_unknown_engine_is_a_configuration_error():
    with configure("bing"), pytest.raises(ValueError):
        global_config.get_default_chat_search_engine()


def test_the_api_key_is_read_from_the_deployment_secret():
    with configure("tavily", SECRET_ARN), patch(
        "app.repositories.models.custom_bot.get_api_key_from_secret_manager",
        return_value="deployment-key",
    ) as get_key, patch.object(
        internet_search, "_search_with_tavily", return_value=[]
    ) as tavily:
        internet_search._search(None, "weather", "en-us", "w")

    get_key.assert_called_once_with(SECRET_ARN)
    assert tavily.call_args.args[1] == "deployment-key"


@pytest.mark.parametrize("secret_arn, key", [("", "unused"), (SECRET_ARN, "")])
def test_a_keyed_engine_without_a_key_fails_without_another_engine(secret_arn, key):
    with configure("brave", secret_arn), patch(
        "app.repositories.models.custom_bot.get_api_key_from_secret_manager",
        return_value=key,
    ), patch.object(internet_search, "_search_with_duckduckgo_standalone") as ddg:
        with pytest.raises(RuntimeError):
            internet_search._search(None, "weather", "en-us", "w")
    ddg.assert_not_called()
