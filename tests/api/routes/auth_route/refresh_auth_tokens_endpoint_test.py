"""
Tests for the refresh auth tokens endpoint.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

import uuid
from typing import TYPE_CHECKING
from unittest import mock

import pytest
from fastapi import status

from lnkr.api.routes import auth_route
from lnkr.config.application_settings import application_settings
from lnkr.exceptions import RefreshTokenGenerationError
from lnkr.services.tokens.access_token_service import decode_access_token

if TYPE_CHECKING:
    from httpx2 import AsyncClient

    from lnkr.models import User


@pytest.mark.usefixtures("override_verify_frontend_api_key")
async def test_refresh_auth_tokens__missing_frontend_api_key(client: AsyncClient) -> None:
    response = await client.post(
        url=f"{application_settings.AUTH_PREFIX}/refresh-auth-tokens",
    )
    data = response.json()

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    error = data["detail"][0]
    assert error["msg"] == "The provided frontend api key is invalid"
    assert error["type"] == "frontend_api_key_invalid"


async def test_refresh_auth_tokens__refresh_token_invalid(client: AsyncClient) -> None:
    response = await client.post(
        url=f"{application_settings.AUTH_PREFIX}/refresh-auth-tokens",
        json={"refresh_token_value": ""},
    )
    data = response.json()

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    error = data["detail"][0]
    assert error["msg"] == "The provided refresh token is invalid, used, revoked or has expired"
    assert error["type"] == "refresh_token_invalid"


async def test_refresh_auth_tokens__refresh_token_generation_failure(client: AsyncClient) -> None:
    with mock.patch.object(
        auth_route,
        "rotate_refresh_token",
        mock.AsyncMock(side_effect=RefreshTokenGenerationError()),
    ):
        response = await client.post(
            url=f"{application_settings.AUTH_PREFIX}/refresh-auth-tokens",
            json={"refresh_token_value": "value"},
        )

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    error = response.json()["detail"][0]
    assert error["msg"] == "Unable to generate a refresh token. Please try again."
    assert error["type"] == "refresh_token_generation_failed"


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
    error = response.json()["detail"][0]
    assert error["msg"] == f"User with id '{user_id}' does not exist"
    assert error["type"] == "user_does_not_exist"


async def test_refresh_auth_tokens__refresh_token_valid(
    client: AsyncClient,
    issued_auth_tokens: dict[str, str],
    user: User,
) -> None:
    original_refresh_token = issued_auth_tokens["refresh_token"]

    response = await client.post(
        url=f"{application_settings.AUTH_PREFIX}/refresh-auth-tokens",
        json={"refresh_token_value": original_refresh_token},
    )
    data = response.json()
    access_token_payload = decode_access_token(data["access_token"])

    assert response.status_code == status.HTTP_200_OK
    assert set(data.keys()) == {"access_token", "refresh_token", "token_type"}
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["refresh_token"] != original_refresh_token
    assert data["token_type"] == "bearer"  # noqa: S105
    assert access_token_payload.sub == str(user.id)
    assert access_token_payload.type == "access"
