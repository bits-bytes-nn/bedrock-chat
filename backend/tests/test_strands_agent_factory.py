from unittest.mock import MagicMock, patch

from app.strands_integration.agent import factory
from app.strands_integration.agent.factory import create_strands_agent
from strands.agent import NullConversationManager


def test_context_overflow_is_not_hidden_by_dropping_messages():
    agent = create_strands_agent(
        bot=None, instructions=[], model_name="claude-v5.5-haiku"
    )
    assert isinstance(agent.conversation_manager, NullConversationManager)


def test_prompt_caching_follows_the_tools_that_the_agent_really_gets():
    # A bot with tools on a model without tool use gets no tools.
    bot = MagicMock()
    bot.is_agent_enabled.return_value = True
    with patch.object(
        factory, "get_system_prompt", wraps=factory.get_system_prompt
    ) as system_prompt, patch(
        "app.strands_integration.utils.is_tooluse_supported", return_value=False
    ):
        agent = factory.create_strands_agent(
            bot=bot, instructions=[], model_name="claude-v5.5-haiku"
        )

    assert agent.tool_names == []
    assert system_prompt.call_args.kwargs["has_tools"] is False
