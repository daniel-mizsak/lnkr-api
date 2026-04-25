"""
High level services for access token management.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import jwt

from lnkr.config.application_settings import application_settings
from lnkr.models import AccessTokenPayload

if TYPE_CHECKING:
    import uuid


def create_access_token(user_id: uuid.UUID) -> str:
    """Create an access token for a given user id."""
    payload = {
        "sub": str(user_id),
        "iat": datetime.now(tz=UTC),
        "exp": datetime.now(tz=UTC) + timedelta(minutes=application_settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "type": "access",
    }
    return jwt.encode(
        payload,
        key=application_settings.ACCESS_TOKEN_SECRET_KEY.get_secret_value(),
        algorithm=application_settings.ACCESS_TOKEN_ALGORITHM,
    )


def decode_access_token(token: str) -> AccessTokenPayload:
    """Decode an access token and return its payload."""
    payload = jwt.decode(
        token,
        key=application_settings.ACCESS_TOKEN_SECRET_KEY.get_secret_value(),
        algorithms=[application_settings.ACCESS_TOKEN_ALGORITHM],
    )
    access_token_payload = AccessTokenPayload.model_validate(payload)
    if access_token_payload.type != "access":
        raise jwt.InvalidTokenError
    return access_token_payload
