"""
Tests for the verify login token endpoint.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

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
async def test_verify_login_token__missing_frontend_api_key(client: AsyncClient) -> None:
    response = await client.post(
        url=f"{application_settings.AUTH_PREFIX}/verify-login-token",
    )
    data = response.json()

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    error = data["detail"][0]
    assert error["msg"] == "The provided frontend api key is invalid"
    assert error["type"] == "frontend_api_key_invalid"


async def test_verify_login_token__login_token_invalid(client: AsyncClient) -> None:
    response = await client.post(
        url=f"{application_settings.AUTH_PREFIX}/verify-login-token",
        json={"login_token_value": ""},
    )
    data = response.json()

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    error = data["detail"][0]
    assert error["msg"] == "The provided login token is invalid, used or has expired"
    assert error["type"] == "login_token_invalid"


async def test_verify_login_token__refresh_token_generation_failure(
    client: AsyncClient,
    issued_login_token: str,
) -> None:
    with mock.patch.object(
        auth_route,
        "create_and_save_refresh_token",
        mock.AsyncMock(side_effect=RefreshTokenGenerationError()),
    ):
        response = await client.post(
            url=f"{application_settings.AUTH_PREFIX}/verify-login-token",
            json={"login_token_value": issued_login_token},
        )

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    error = response.json()["detail"][0]
    assert error["msg"] == "Unable to generate a refresh token. Please try again."
    assert error["type"] == "refresh_token_generation_failed"


async def test_verify_login_token__login_token_valid(client: AsyncClient, issued_login_token: str, user: User) -> None:
    response = await client.post(
        url=f"{application_settings.AUTH_PREFIX}/verify-login-token",
        json={"login_token_value": issued_login_token},
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert set(data.keys()) == {"access_token", "refresh_token", "token_type"}
    assert data["access_token"]
    access_token_payload = decode_access_token(data["access_token"])
    assert access_token_payload.sub == str(user.id)
    assert access_token_payload.type == "access"
    assert data["refresh_token"]
    assert data["token_type"] == "bearer"  # noqa: S105
