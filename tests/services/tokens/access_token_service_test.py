"""
Tests for the access token service.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import jwt
import pytest
import time_machine

from lnkr.config.application_settings import application_settings
from lnkr.services.tokens.access_token_service import create_access_token, decode_access_token

if TYPE_CHECKING:
    import uuid


@pytest.mark.usefixtures("frozen_now")
def test_create_and_decode_access_token__round_trip(user_id: uuid.UUID, now: datetime) -> None:
    token = create_access_token(user_id)
    payload = decode_access_token(token)

    assert payload.sub == str(user_id)
    assert payload.type == "access"
    assert payload.iat == now
    assert payload.exp == now + timedelta(minutes=application_settings.ACCESS_TOKEN_EXPIRE_MINUTES)


@pytest.mark.usefixtures("frozen_now")
def test_decode_access_token__wrong_token_type(user_id: uuid.UUID, now: datetime) -> None:
    token = jwt.encode(
        {"sub": str(user_id), "iat": now, "exp": now + timedelta(minutes=1), "type": "refresh"},
        key=application_settings.ACCESS_TOKEN_SECRET_KEY.get_secret_value(),
        algorithm=application_settings.ACCESS_TOKEN_ALGORITHM,
    )

    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token)


@pytest.mark.usefixtures("frozen_now")
def test_decode_access_token__invalid_signature(user_id: uuid.UUID, now: datetime) -> None:
    token = jwt.encode(
        {"sub": str(user_id), "iat": now, "exp": now + timedelta(minutes=1), "type": "access"},
        key="wrong-secret" * 4,
        algorithm=application_settings.ACCESS_TOKEN_ALGORITHM,
    )

    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token)


def test_decode_access_token__immediately_before_expiration(user_id: uuid.UUID) -> None:
    expires_at = datetime(2026, 1, 1, 12, tzinfo=UTC)
    token = jwt.encode(
        {"sub": str(user_id), "iat": expires_at - timedelta(minutes=1), "exp": expires_at, "type": "access"},
        key=application_settings.ACCESS_TOKEN_SECRET_KEY.get_secret_value(),
        algorithm=application_settings.ACCESS_TOKEN_ALGORITHM,
    )

    with time_machine.travel(expires_at - timedelta(microseconds=1), tick=False):
        payload = decode_access_token(token)

    assert payload.sub == str(user_id)
    assert payload.exp == expires_at


@pytest.mark.parametrize(
    "elapsed",
    [pytest.param(timedelta(0), id="at-expiration"), pytest.param(timedelta(microseconds=1), id="after-expiration")],
)
def test_decode_access_token__expired_token(user_id: uuid.UUID, elapsed: timedelta) -> None:
    expires_at = datetime(2026, 1, 1, 12, tzinfo=UTC)
    token = jwt.encode(
        {"sub": str(user_id), "iat": expires_at - timedelta(minutes=1), "exp": expires_at, "type": "access"},
        key=application_settings.ACCESS_TOKEN_SECRET_KEY.get_secret_value(),
        algorithm=application_settings.ACCESS_TOKEN_ALGORITHM,
    )

    with time_machine.travel(expires_at + elapsed, tick=False), pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token)
