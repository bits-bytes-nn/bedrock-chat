"""
Strands integration utilities - Independent tool management.
"""

import logging
from collections.abc import Callable

from app.bedrock import is_tooluse_supported
from app.repositories.models.custom_bot import BotModel
from app.routes.schemas.conversation import type_model_name
from app.usecases.global_config import get_default_chat_search_engine
from strands.types.tools import AgentTool as StrandsAgentTool

logger = logging.getLogger(__name__)


def _tool_factories() -> dict[str, Callable[[BotModel | None], StrandsAgentTool]]:
    """The tools that a bot can turn on, by tool name."""
    from app.strands_integration.tools.bedrock_agent import create_bedrock_agent_tool
    from app.strands_integration.tools.internet_search import (
        create_internet_search_tool,
    )

    return {
        "internet_search": create_internet_search_tool,
        "bedrock_agent": create_bedrock_agent_tool,
    }


def get_strands_registered_tools() -> list[StrandsAgentTool]:
    """The tools that bots can turn on, without the settings of a bot."""
    return [create(None) for create in _tool_factories().values()]


def get_strands_tools(
    bot: BotModel | None, model_name: type_model_name
) -> list[StrandsAgentTool]:
    """Get Strands tools based on bot configuration."""
    if not is_tooluse_supported(model_name):
        logger.warning(
            f"Tool use is not supported for model {model_name}. Returning empty tool list."
        )
        return []

    if bot is None:
        # Chats without a bot get the internet search of the deployment, if any.
        if get_default_chat_search_engine() is None:
            return []
        from app.strands_integration.tools.internet_search import (
            create_internet_search_tool,
        )

        return [create_internet_search_tool(None)]

    if not bot.is_agent_enabled():
        return []

    # Only the tools that the bot turned on are created: creating the Bedrock Agent
    # tool calls the Bedrock Agents API.
    factories = _tool_factories()
    tools: list[StrandsAgentTool] = [
        factories[tool.name](bot) for tool in bot.agent.tools if tool.name in factories
    ]

    # Add knowledge tool if bot has knowledge base
    if bot.has_knowledge():
        from app.strands_integration.tools.knowledge_search import (
            create_knowledge_search_tool,
        )

        knowledge_tool = create_knowledge_search_tool(bot)
        tools.append(knowledge_tool)

    if len(tools) == 0:
        logger.warning("No tools configured for bot. Returning empty tool list.")
        return []

    logger.info(f"Strands tools configured for bot: {[t.tool_name for t in tools]}")
    return tools
