from app.strands_integration.agent.factory import create_strands_agent
from strands.agent import NullConversationManager


def test_context_overflow_is_not_hidden_by_dropping_messages():
    agent = create_strands_agent(
        bot=None, instructions=[], model_name="claude-v5.5-haiku"
    )
    assert isinstance(agent.conversation_manager, NullConversationManager)
