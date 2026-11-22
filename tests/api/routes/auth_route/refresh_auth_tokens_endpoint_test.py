"""
Tests for the refresh auth tokens endpoint.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

import logging
import uuid
from typing import TYPE_CHECKING
from unittest import mock

import pytest
from fastapi import status

from lnkr.api.routes import auth_route
from lnkr.config.application_settings import application_settings
from lnkr.exceptions import RefreshTokenGenerationFailedError
from lnkr.services.tokens.access_token_service import decode_access_token

if TYPE_CHECKING:
    from httpx2 import AsyncClient

    from lnkr.models import User


@pytest.mark.usefixtures("override_verify_frontend_api_key")
async def test_refresh_auth_tokens__missing_frontend_api_key(client: AsyncClient) -> None:
    response = await client.post(
        url=f"{application_settings.AUTH_PREFIX}/refresh-auth-tokens",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    data = response.json()
    error = data["detail"][0]

    assert error["msg"] == "The provided frontend api key is invalid"
    assert error["type"] == "frontend_api_key_invalid"


async def test_refresh_auth_tokens__invalid_refresh_token(
    client: AsyncClient,
) -> None:
    response = await client.post(
        url=f"{application_settings.AUTH_PREFIX}/refresh-auth-tokens",
        json={"refresh_token_value": ""},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    data = response.json()
    error = data["detail"][0]

    assert error["msg"] == "The provided refresh token is invalid, used, revoked or has expired"
    assert error["type"] == "refresh_token_invalid"


async def test_refresh_auth_tokens__refresh_token_generation_failure(
    client: AsyncClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    generation_error = RefreshTokenGenerationFailedError()

    with mock.patch.object(
        auth_route,
        "rotate_refresh_token",
        mock.AsyncMock(side_effect=generation_error),
    ):
        response = await client.post(
            url=f"{application_settings.AUTH_PREFIX}/refresh-auth-tokens",
            json={"refresh_token_value": "value"},
        )

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    data = response.json()
    error = data["detail"][0]

    assert error["msg"] == "Unable to generate a refresh token. Please try again."
    assert error["type"] == "refresh_token_generation_failed"
    assert (
        "lnkr.api.exception_handlers",
        logging.ERROR,
        "Refresh token generation attempts exhausted",
    ) in caplog.record_tuples


async def test_refresh_auth_tokens__user_does_not_exist(client: AsyncClient) -> None:
    user_id = uuid.uuid4()

    with mock.patch.object(
        auth_route,
        "rotate_refresh_token",
        mock.AsyncMock(return_value=(user_id, "new-refresh-token")),
    ):
        response = await client.post(
            url=f"{application_settings.AUTH_PREFIX}/refresh-auth-tokens",
            json={"refresh_token_value": "value"},
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND

    data = response.json()
    error = data["detail"][0]

    assert error["msg"] == f"User with id '{user_id}' does not exist"
    assert error["type"] == "user_does_not_exist"


async def test_refresh_auth_tokens__valid_refresh_token(
    client: AsyncClient,
    issued_auth_tokens: dict[str, str],
    user: User,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="lnkr.api.routes.auth_route")
    original_refresh_token = issued_auth_tokens["refresh_token"]

    response = await client.post(
        url=f"{application_settings.AUTH_PREFIX}/refresh-auth-tokens",
        json={"refresh_token_value": original_refresh_token},
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    access_token_payload = decode_access_token(data["access_token"])

    assert set(data.keys()) == {"access_token", "refresh_token", "token_type"}
    assert access_token_payload.sub == str(user.id)
    assert data["refresh_token"]
    assert data["refresh_token"] != original_refresh_token
    assert data["token_type"] == "bearer"  # noqa: S105
    assert (
        "lnkr.api.routes.auth_route",
        logging.INFO,
        f"Authentication tokens refreshed for user {user.id}",
    ) in caplog.record_tuples
