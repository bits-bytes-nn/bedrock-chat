"""Authorizer of the WebSocket `$connect` route.

Browsers cannot set headers on a WebSocket, so the client passes its ID token in the
`token` query string parameter. The token is checked again when a message starts.
"""

import logging

from app.auth import verify_token

logger = logging.getLogger(__name__)


def handler(event: dict, context) -> dict:
    token = (event.get("queryStringParameters") or {}).get("token", "")
    try:
        claims = verify_token(token)
        principal, effect = claims["sub"], "Allow"
    except Exception as e:
        # Only the reason is logged; the token stays out of the logs.
        # WARNING, because the runtime drops INFO; failing to fetch the signing keys
        # would otherwise reject everyone without a trace.
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
