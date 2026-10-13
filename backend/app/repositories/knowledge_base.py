import functools

from app.routes.schemas.bot_kb import type_kb_resource_type
from app.utils import get_bedrock_agent_client


@functools.cache
def get_knowledge_base_type(knowledge_base_id: str) -> type_kb_resource_type:
    """Return the type of the knowledge base, which never changes after creation.

    Raises:
        botocore.exceptions.ClientError: If the knowledge base cannot be read.
    """
    response = get_bedrock_agent_client().get_knowledge_base(
        knowledgeBaseId=knowledge_base_id
    )
    return response["knowledgeBase"]["knowledgeBaseConfiguration"]["type"]
