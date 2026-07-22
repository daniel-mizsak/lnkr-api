"""
Tests for the access token service.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import jwt
import pytest

from lnkr.config.application_settings import application_settings
from lnkr.services.tokens.access_token_service import create_access_token, decode_access_token

if TYPE_CHECKING:
    import uuid


def test_create_and_decode_access_token__round_trip(user_id: uuid.UUID) -> None:
    before = datetime.now(tz=UTC)

    payload = decode_access_token(create_access_token(user_id))

    assert payload.sub == str(user_id)
    assert payload.type == "access"
    assert before - timedelta(seconds=1) <= payload.iat <= datetime.now(tz=UTC)
    assert payload.exp - payload.iat == timedelta(minutes=application_settings.ACCESS_TOKEN_EXPIRE_MINUTES)


def test_decode_access_token__rejects_wrong_token_type(user_id: uuid.UUID) -> None:
    now = datetime.now(tz=UTC)
    token = jwt.encode(
        {"sub": str(user_id), "iat": now, "exp": now + timedelta(minutes=1), "type": "refresh"},
        key=application_settings.ACCESS_TOKEN_SECRET_KEY.get_secret_value(),
        algorithm=application_settings.ACCESS_TOKEN_ALGORITHM,
    )

    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token)


def test_decode_access_token__rejects_invalid_signature(user_id: uuid.UUID) -> None:
    now = datetime.now(tz=UTC)
    token = jwt.encode(
        {"sub": str(user_id), "iat": now, "exp": now + timedelta(minutes=1), "type": "access"},
        key="wrong-secret" * 4,
        algorithm=application_settings.ACCESS_TOKEN_ALGORITHM,
    )

    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token)
