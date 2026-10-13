"""Authorizer of the WebSocket `$connect` route.

Browsers cannot set headers on a WebSocket, so the client passes its ID token in the
`token` query string parameter. The token is checked again when a message starts.
"""

import logging

import requests
from app.auth import verify_token

logger = logging.getLogger(__name__)


def handler(event: dict, context) -> dict:
    token = (event.get("queryStringParameters") or {}).get("token", "")
    try:
        claims = verify_token(token)
        principal, effect = claims["sub"], "Allow"
    except requests.RequestException as e:
        # Rejects every connection until the keys can be fetched again. Only the
        # exception type is logged; the token stays out of the logs.
        logger.error("Failed to fetch the signing keys: %s", type(e).__name__)
        principal, effect = "anonymous", "Deny"
    except Exception as e:
        # WARNING, because the runtime drops INFO.
        logger.warning("Rejected a connection: %s", type(e).__name__)
        principal, effect = "anonymous", "Deny"
    return {
        "principalId": principal,
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "execute-api:Invoke",
                    "Effect": effect,
                    "Resource": event["methodArn"],
                }
            ],
        },
    }
