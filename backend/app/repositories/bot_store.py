import logging
import os
import random
import time

from app.repositories.common import get_opensearch_client
from app.repositories.models.custom_bot import BotMeta
from app.user import User
from opensearchpy import OpenSearch

env_prefix = os.environ.get("ENV_PREFIX", "")
INDEX_NAME = f"{env_prefix}bot"

logger = logging.getLogger(__name__)


def _accessible_bots_filter(user: User) -> dict:
    """Filter for the bots the user can find: the same rules as
    `BotModel.is_accessible_by_user`, except that private bots of other users are
    not listed even for admins."""
    owned = {
        "bool": {
            "must": [
                {"term": {"PK.keyword": user.id}},
                {
                    "bool": {
                        "should": [
                            {
                                "bool": {
                                    "must_not": {"exists": {"field": "SharedScope"}}
                                }
                            },
                            {"term": {"SharedScope.keyword": "partial"}},
                        ],
                        "minimum_should_match": 1,
                    }
                },
            ]
        }
    }
    partial: dict = {"term": {"SharedScope.keyword": "partial"}}
    if not user.is_admin():
        partial = {
            "bool": {
                "must": [
                    partial,
                    {
                        "bool": {
                            "should": [
                                {"term": {"AllowedCognitoUsers.keyword": user.id}},
                                {
                                    "terms": {
                                        "AllowedCognitoGroups.keyword": user.groups
                                    }
                                },
                            ],
                            "minimum_should_match": 1,
                        }
                    },
                ]
            }
        }
    return {
        "bool": {
            "must": [{"prefix": {"SK.keyword": "BOT"}}],
            "should": [{"term": {"SharedScope.keyword": "all"}}, owned, partial],
            "minimum_should_match": 1,
        }
    }


def find_bots_by_query(
    query: str,
    user: User,
    limit: int = 20,
    client: OpenSearch | None = None,
) -> list[BotMeta]:
    """Search bots by query string.
    This method is used for bot-store functionality.

    Query Structure Explanation:

    1. Main Search (must clause):
    - Uses multi_match for flexible text searching
    - Searches the description and title. Instructions are private to the owner.
    - Implements fuzzy matching for typo tolerance
    - Requires 30% of search terms to match

    2. Access Control (filter clause):
    The filter implements three access levels:
    a) Public Bots (`SharedScope = "all"`):
        - Available to all users

    b) Partial Shared Bots (`SharedScope = "partial"`):
        - Admins can see all of them
        - Non-admins can see them if they are listed in `AllowedCognitoUsers`
          or belong to `AllowedCognitoGroups`

    c) Private Bots (no `SharedScope` field):
        - Only accessible to the owner (`PK.keyword = user.id`)
        - Admins can see their own private bots (`PK.keyword = admin-user`)
    """
    client = client or get_opensearch_client()
    logger.info("Searching bots")

    access_filter = _accessible_bots_filter(user)

    search_body = {
        "query": {
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": query,
                            "fields": ["Description", "Title"],
                            "type": "best_fields",
                            "operator": "or",
                            "minimum_should_match": "30%",
                            "fuzziness": "AUTO",
                        }
                    }
                ],
                "filter": access_filter,
            }
        },
        "size": limit,
    }

    response = client.search(index=INDEX_NAME, body=search_body)
    bots = [
        BotMeta.from_opensearch_response(hit, user.id)
        for hit in response["hits"]["hits"]
    ]
    logger.info("Found %d bots", len(bots))
    return bots


def find_bots_sorted_by_usage_count(
    user: User,
    limit: int = 20,
    client: OpenSearch | None = None,
) -> list[BotMeta]:
    """Search bots sorted by usage count while considering access control."""
    client = client or get_opensearch_client()
    logger.info(f"Searching bots sorted by usage count")

    access_filter = _accessible_bots_filter(user)

    search_body = {
        "query": {"bool": {"filter": access_filter}},
        "sort": [{"UsageStats.usage_count": {"order": "desc"}}],
        "size": limit,
    }

    response = client.search(index=INDEX_NAME, body=search_body)
    bots = [
        BotMeta.from_opensearch_response(hit, user.id)
        for hit in response["hits"]["hits"]
    ]
    logger.info(f"Found {len(bots)} bots sorted by usage count")
    return bots


def find_random_bots(
    user: User,
    limit: int = 20,
    client: OpenSearch | None = None,
) -> list[BotMeta]:
    """Find random bots while considering access control."""
    client = client or get_opensearch_client()
    logger.info(f"Searching random bots")

    access_filter = _accessible_bots_filter(user)

    seed = int(time.time()) + random.randint(0, 10000)
    search_body = {
        "query": {
            "function_score": {
                "query": {"bool": {"filter": access_filter}},
                "random_score": {"seed": seed},
            }
        },
        "size": limit,
    }

    response = client.search(index=INDEX_NAME, body=search_body)
    bots = [
        BotMeta.from_opensearch_response(hit, user.id)
        for hit in response["hits"]["hits"]
    ]
    logger.info(f"Found {len(bots)} random bots")
    return bots
