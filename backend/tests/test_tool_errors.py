"""Tool failures reach the model and the stored conversation as fixed texts."""

from unittest.mock import MagicMock, patch

import pytest
from app.strands_integration.tools import bedrock_agent, internet_search
from app.strands_integration.tools.knowledge_search import (
    create_knowledge_search_tool,
)

SECRET = "arn:aws:secretsmanager:us-east-1:123456789012:secret:internal"


def knowledge_search():
    bot = MagicMock()
    bot.has_knowledge.return_value = True
    tool = create_knowledge_search_tool(bot)
    with patch(
        "app.vector_search.search_related_docs", side_effect=RuntimeError(SECRET)
    ):
        return tool(query="q")


def internet():
    tool = internet_search.create_internet_search_tool(None)
    with patch.object(
        internet_search,
        "_search_with_duckduckgo_standalone",
        side_effect=RuntimeError(SECRET),
    ):
        return tool(query="q")


def agent():
    with patch.object(
        bedrock_agent,
        "_get_bedrock_agent_config",
        return_value=MagicMock(agent_id="a", alias_id="b"),
    ):
        tool = bedrock_agent.create_bedrock_agent_tool(MagicMock())
        with patch.object(
            bedrock_agent,
            "_invoke_bedrock_agent_standalone",
            side_effect=RuntimeError(SECRET),
        ):
            return tool(query="q")


@pytest.mark.parametrize("run", [knowledge_search, internet, agent])
def test_tool_errors_do_not_expose_the_exception(run, caplog):
    result = run()

    assert result["status"] == "error"
    assert SECRET not in str(result["content"])
    # The details stay in the logs.
    assert any(record.exc_info for record in caplog.records)
