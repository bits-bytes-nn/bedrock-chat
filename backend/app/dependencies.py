from app.auth import verify_token
from app.user import User
from fastapi import Depends, HTTPException, Request, status
from jwt import PyJWTError


def user_from_token(token: str) -> User:
    try:
        return User.from_decoded_token(verify_token(token))
    except (KeyError, PyJWTError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(request: Request) -> User:
    """The user that the middleware authenticated, so the token is verified once."""
    user = getattr(request.state, "current_user", None)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    return user


def check_admin(user: User = Depends(get_current_user)):
    if not user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can access this API.",
        )


def check_creating_bot_allowed(user: User = Depends(get_current_user)):
    if not user.is_creating_bot_allowed():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not allowed to create bot.",
        )


def check_publish_allowed(user: User = Depends(get_current_user)):
    if not user.is_publish_allowed():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not allowed to publish bot.",
        )
