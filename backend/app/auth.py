import os
import time

import requests
import jwt

REGION = os.environ.get("REGION", "ap-northeast-1")
USER_POOL_ID = os.environ.get("USER_POOL_ID", "")
CLIENT_ID = os.environ.get("CLIENT_ID", "")

ISSUER = f"https://cognito-idp.{REGION}.amazonaws.com/{USER_POOL_ID}"

JWKS_CACHE_TTL_SECONDS = 3600
# Unknown key ids come from the client, so forced refreshes are rate limited.
JWKS_MIN_REFRESH_INTERVAL_SECONDS = 60
_jwks_cache: dict = {"keys": [], "fetched_at": 0.0}


def _get_signing_keys(refresh: bool = False) -> list[dict]:
    """Return the user pool signing keys, fetched at most once per TTL."""
    age = time.monotonic() - _jwks_cache["fetched_at"]
    if (
        not _jwks_cache["keys"]
        or age > JWKS_CACHE_TTL_SECONDS
        or (refresh and age > JWKS_MIN_REFRESH_INTERVAL_SECONDS)
    ):
        url = f"{ISSUER}/.well-known/jwks.json"
        response = requests.get(url, timeout=(3, 5))
        response.raise_for_status()
        _jwks_cache["keys"] = response.json()["keys"]
        _jwks_cache["fetched_at"] = time.monotonic()
    return _jwks_cache["keys"]


def _find_signing_key(kid: str | None) -> dict:
    for refresh in (False, True):
        # Refresh once for an unknown key id in case the user pool rotated its keys.
        for key in _get_signing_keys(refresh=refresh):
            if key["kid"] == kid:
                return key
    raise jwt.InvalidTokenError("Unknown signing key")


def verify_token(token: str) -> dict:
    """Verify a Cognito ID token and return its claims.

    Raises:
        jwt.PyJWTError: If the token is invalid, expired or not an ID token.
    """
    # PyJWT skips the audience check for an empty audience, so fail closed.
    if not CLIENT_ID:
        raise jwt.InvalidTokenError("CLIENT_ID is not configured.")
    header = jwt.get_unverified_header(token)
    key = jwt.PyJWK(_find_signing_key(header.get("kid")))
    decoded = jwt.decode(
        token,
        key,
        algorithms=["RS256"],
        audience=CLIENT_ID,
        issuer=ISSUER,
    )
    # Only ID tokens carry the user attributes that the app relies on.
    if decoded.get("token_use") != "id":
        raise jwt.InvalidTokenError("Not an ID token")
    return decoded
