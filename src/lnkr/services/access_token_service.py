"""
High level database operations for access token management.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

from datetime import UTC, datetime, timedelta

import jwt

from lnkr.config import settings
from lnkr.models import AccessTokenPayload


def create_access_token(email: str) -> str:
    """Create an access token for a given email.

    Args:
        email (str): The email of the user.

    Returns:
        str: The JWT access token.
    """
    payload = {
        "sub": email,
        "iat": datetime.now(tz=UTC),
        "exp": datetime.now(tz=UTC) + timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS),
        "type": "access",
    }
    return jwt.encode(
        payload,
        key=settings.ACCESS_TOKEN_SECRET_KEY,
        algorithm=settings.ACCESS_TOKEN_ALGORITHM,
    )


def decode_access_token(token: str) -> AccessTokenPayload:
    """Decode an access token and return its payload.

    Args:
        token (str): The JWT access token.

    Returns:
        AccessTokenPayload: The access token payload.
    """
    payload = jwt.decode(
        token,
        key=settings.ACCESS_TOKEN_SECRET_KEY,
        algorithms=[settings.ACCESS_TOKEN_ALGORITHM],
    )
    return AccessTokenPayload.model_validate(payload)
