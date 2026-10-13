import logging

from app.repositories.models.custom_bot import BotModel
from strands import tool
from strands.types.tools import AgentTool as StrandsAgentTool

logger = logging.getLogger(__name__)


def _search_knowledge_standalone(bot: BotModel, query: str) -> list:
    """Standalone knowledge search implementation."""
    from app.vector_search import search_related_docs

    logger.info("Running knowledge search")

    search_results = search_related_docs(bot, query=query)

    logger.info("Knowledge search found %d results", len(search_results))
    return search_results


def create_knowledge_search_tool(bot: BotModel | None) -> StrandsAgentTool:
    """Create a knowledge search tool with bot context captured in closure."""

    @tool
    def knowledge_base_tool(query: str) -> dict:
        """
        Search the documents in this bot's knowledge base.

        Use this tool before answering any question that the bot's documents may
        cover, such as names, figures, policies or procedures from the uploaded
        files and web pages. Answer from general knowledge only when the search
        returns nothing relevant.

        Args:
            query: Search query for vector search, full text search, and hybrid search

        Returns:
            list: Search results for citation support
        """
        logger.debug("[KNOWLEDGE_SEARCH_V3] Starting search")

        try:
            # # Bot is captured on closure
            current_bot = bot

            if not current_bot:
                logger.warning("[KNOWLEDGE_SEARCH_V3] No bot context available")
                return {
                    "status": "error",
                    "content": [
                        {
                            "text": f"Knowledge search requires bot configuration. Query was: {query}"
                        }
                    ],
                }

            # Check if bot has knowledge base
            if not current_bot.has_knowledge():
                logger.warning(
                    "[KNOWLEDGE_SEARCH_V3] Bot has no knowledge base configured"
                )
                return {
                    "status": "error",
                    "content": [
                        {
                            "text": f"Bot does not have a knowledge base configured. Query was: {query}"
                        }
                    ],
                }

            logger.debug(
                f"[KNOWLEDGE_SEARCH_V3] Executing search with bot: {current_bot.id}"
            )

            # Run knowledge search
            results = _search_knowledge_standalone(current_bot, query)

            logger.debug(f"[KNOWLEDGE_SEARCH_V3] Search completed successfully")
            return {
                "status": "success",
                "content": [{"json": result} for result in results],
            }

        except Exception:
            # Error texts can name internal resources; the model and the
            # conversation get a fixed text.
            logger.exception("[KNOWLEDGE_SEARCH_V3] Knowledge search failed")
            return {
                "status": "error",
                "content": [{"text": "The knowledge search failed."}],
            }

    return knowledge_base_tool
