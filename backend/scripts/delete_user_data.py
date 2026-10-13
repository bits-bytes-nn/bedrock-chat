"""Delete the data of a user, for example after removing them from Cognito.

Deletes the user's conversations (with large messages and related documents) and
every bot-table item of the user. Deleting a bot item triggers the removal stream,
which deletes the bot's knowledge base stack, documents, secrets, published API and
its conversations. Bots of other users that this user shared are not affected.

Run from `backend` with credentials for the deployment account:

    CONVERSATION_TABLE_NAME=... BOT_TABLE_NAME=... LARGE_MESSAGE_BUCKET=... \\
    REGION=... poetry run python scripts/delete_user_data.py <user-id> [--yes]

The user id is the Cognito `sub` (the Username in the user pool). Without `--yes`,
the script only lists what it would delete.
"""

import argparse
import logging

from app.repositories.common import get_bot_table_client
from app.repositories.conversation import (
    delete_conversation_by_user_id,
    find_conversation_by_user_id,
)
from boto3.dynamodb.conditions import Key

logger = logging.getLogger("delete_user_data")


def _bot_table_keys(user_id: str) -> list[dict]:
    table = get_bot_table_client()
    query: dict = {
        "KeyConditionExpression": Key("PK").eq(user_id),
        "ProjectionExpression": "PK, SK",
    }
    keys: list[dict] = []
    while True:
        response = table.query(**query)
        keys.extend(response["Items"])
        if "LastEvaluatedKey" not in response:
            return keys
        query["ExclusiveStartKey"] = response["LastEvaluatedKey"]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("user_id")
    parser.add_argument("--yes", action="store_true", help="delete the data")
    args = parser.parse_args()

    conversations = find_conversation_by_user_id(args.user_id)
    bot_keys = _bot_table_keys(args.user_id)
    bots = [k for k in bot_keys if k["SK"].startswith("BOT#")]
    logger.info(
        "User %s: %d conversations, %d bots, %d other bot-table items",
        args.user_id,
        len(conversations),
        len(bots),
        len(bot_keys) - len(bots),
    )
    if not args.yes:
        logger.info("Nothing deleted; run again with --yes to delete.")
        return

    delete_conversation_by_user_id(args.user_id)
    with get_bot_table_client().batch_writer() as writer:
        for key in bot_keys:
            writer.delete_item(Key=key)
    logger.info(
        "Deleted. The removal stream now cleans up the bots' resources; "
        "check the BotRemovalFailures alarm."
    )


if __name__ == "__main__":
    main()
