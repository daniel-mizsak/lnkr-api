"""
Tests for the revoke refresh token endpoint.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING

import pytest
from fastapi import status

from lnkr.config.application_settings import application_settings

if TYPE_CHECKING:
    from httpx2 import AsyncClient


@pytest.mark.usefixtures("override_verify_frontend_api_key")
async def test_revoke_refresh_token__missing_frontend_api_key(client: AsyncClient) -> None:
    response = await client.post(url=f"{application_settings.AUTH_PREFIX}/revoke-refresh-token")
    data = response.json()

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    error = data["detail"][0]
    assert error["msg"] == "The provided frontend api key is invalid"
    assert error["type"] == "frontend_api_key_invalid"


async def test_revoke_refresh_token__refresh_token_invalid(client: AsyncClient) -> None:
    response = await client.post(
        url=f"{application_settings.AUTH_PREFIX}/revoke-refresh-token",
        json={"refresh_token_value": ""},
    )
    data = response.json()

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    error = data["detail"][0]
    assert error["msg"] == "The provided refresh token is invalid, used, revoked or has expired"
    assert error["type"] == "refresh_token_invalid"


async def test_revoke_refresh_token__refresh_token_valid(
    client: AsyncClient, issued_auth_tokens: dict[str, str]
) -> None:
    refresh_token_value = issued_auth_tokens["refresh_token"]

    response = await client.post(
        url=f"{application_settings.AUTH_PREFIX}/revoke-refresh-token",
        json={"refresh_token_value": refresh_token_value},
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
