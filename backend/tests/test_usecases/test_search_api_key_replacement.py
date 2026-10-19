from unittest.mock import patch

import pytest
from app.repositories.models.custom_bot import (
    AgentModel,
    InternetToolModel,
    SearchApiConfigModel,
)
from app.usecases import bot as bot_usecase


def agent(engine: str | None) -> AgentModel:
    if engine is None:
        return AgentModel(tools=[])
    config = (
        None
        if engine == "duckduckgo"
        else SearchApiConfigModel(secret_arn="arn", api_key="k", max_results=5)
    )
    return AgentModel(
        tools=[
            InternetToolModel(
                name="internet_search",
                description="",
                search_engine=engine,
                search_api_config=config,
            )
        ]
    )


@pytest.mark.parametrize(
    "before, after, deleted",
    [
        ("tavily", "brave", "tavily"),
        ("firecrawl", "duckduckgo", "firecrawl"),
        ("brave", None, "brave"),
        ("tavily", "tavily", None),
        ("duckduckgo", "tavily", None),
        (None, "brave", None),
    ],
)
def test_saving_deletes_only_the_key_the_bot_stopped_using(before, after, deleted):
    with patch.object(bot_usecase, "delete_api_key_from_secret_manager") as delete:
        bot_usecase._delete_replaced_search_api_key(
            "owner", "bot", agent(before), agent(after)
        )

    if deleted:
        delete.assert_called_once_with("owner", "bot", deleted)
    else:
        delete.assert_not_called()


def test_a_failed_deletion_does_not_fail_the_saved_bot(caplog):
    with patch.object(
        bot_usecase,
        "delete_api_key_from_secret_manager",
        side_effect=RuntimeError("throttled"),
    ):
        bot_usecase._delete_replaced_search_api_key(
            "owner", "bot", agent("tavily"), agent(None)
        )

    assert "replaced tavily key" in caplog.text
