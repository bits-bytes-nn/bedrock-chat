import os
import time

import requests
from jose import JWTError, jwt

REGION = os.environ.get("REGION", "ap-northeast-1")
USER_POOL_ID = os.environ.get("USER_POOL_ID", "")
CLIENT_ID = os.environ.get("CLIENT_ID", "")

JWKS_CACHE_TTL_SECONDS = 3600
_jwks_cache: dict = {"keys": [], "fetched_at": 0.0}


def _get_signing_keys(refresh: bool = False) -> list[dict]:
    """Return the user pool signing keys, fetched at most once per TTL."""
    expired = time.monotonic() - _jwks_cache["fetched_at"] > JWKS_CACHE_TTL_SECONDS
    if refresh or expired or not _jwks_cache["keys"]:
        url = f"https://cognito-idp.{REGION}.amazonaws.com/{USER_POOL_ID}/.well-known/jwks.json"
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
    raise JWTError("Unknown signing key")


def verify_token(token: str) -> dict:
    header = jwt.get_unverified_header(token)
    key = _find_signing_key(header.get("kid"))
    # The JWT returned from the Identity Provider may contain an at_hash
    # jose jwt.decode verifies id_token with access_token by default if it contains at_hash
    # See : https://github.com/mpdavis/python-jose/blob/4b0701b46a8d00988afcc5168c2b3a1fd60d15d8/jose/jwt.py#L59
    # Since we are not using an access token in the app, skipping the verification of the at_hash.
    # so we will disable the verify_at_hash check.
    decoded = jwt.decode(
        token,
        key,
        algorithms=["RS256"],
        options={"verify_at_hash": False},
        audience=CLIENT_ID,
    )
    return decoded
