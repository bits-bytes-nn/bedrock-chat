import logging
import os

import boto3
from app.user import UserGroup, UserWithoutGroups
from botocore.config import Config
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

USER_POOL_ID = os.environ.get("USER_POOL_ID")
MAX_GROUP_PAGES = 5

# The standard mode retries TooManyRequestsException with backoff. The quotas are
# low (ListUsers 30 RPS, ListGroups 20 RPS, AdminGetUser 120 RPS).
# See: https://docs.aws.amazon.com/cognito/latest/developerguide/quotas.html
client = boto3.client(
    "cognito-idp", config=Config(retries={"mode": "standard", "max_attempts": 3})
)


def find_users_by_email_prefix(prefix: str, limit: int = 10) -> list[UserWithoutGroups]:
    """Find users whose email starts with the prefix.

    Raises:
        ValueError: If the prefix contains characters that end the filter string.
    """
    if '"' in prefix or "\\" in prefix:
        raise ValueError("The prefix must not contain quotes or backslashes.")
    response = client.list_users(
        UserPoolId=USER_POOL_ID, Filter=f'email ^= "{prefix.lower()}"', Limit=limit
    )
    users = response.get("Users", [])
    logger.debug("Found %d users", len(users))
    return [UserWithoutGroups.from_cognito_idp_response(user) for user in users]


def find_group_by_name_prefix(prefix: str) -> list[UserGroup]:
    groups = []
    params = {"UserPoolId": USER_POOL_ID}
    for _ in range(MAX_GROUP_PAGES):
        response = client.list_groups(**params)
        groups.extend(response.get("Groups", []))
        next_token = response.get("NextToken")
        if not next_token:
            break
        params["NextToken"] = next_token
    else:
        logger.warning(
            "Listed %d pages of groups; some groups were not searched.",
            MAX_GROUP_PAGES,
        )

    # Cognito cannot filter groups by prefix.
    return [
        UserGroup.from_cognito_idp_response(group)
        for group in groups
        if group["GroupName"].lower().startswith(prefix.lower())
    ]


def find_user_by_id(id: str) -> UserWithoutGroups | None:
    try:
        response = client.admin_get_user(UserPoolId=USER_POOL_ID, Username=id)
    except ClientError as e:
        if e.response["Error"]["Code"] == "UserNotFoundException":
            return None
        raise
    return UserWithoutGroups.from_cognito_idp_response(response)
