"""
Tests for the revoke refresh token endpoint.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING

from fastapi import status

from lnkr.config.application_settings import application_settings

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def test_revoke_refresh_token__refresh_token_invalid(client: TestClient) -> None:
    response = client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.AUTH_PREFIX}/revoke-refresh-token",
        json={"refresh_token_value": ""},
    )
    data = response.json()

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    error = data["detail"][0]
    assert error["msg"] == "The provided refresh token is invalid, used, revoked or has expired"
    assert error["type"] == "refresh_token_invalid"


def test_revoke_refresh_token__success(client: TestClient, issued_auth_tokens: dict[str, str]) -> None:
    refresh_token_value = issued_auth_tokens["refresh_token"]

    response = client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.AUTH_PREFIX}/revoke-refresh-token",
        json={"refresh_token_value": refresh_token_value},
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT


def test_revoke_refresh_token__revoked_refresh_token_cannot_be_used(
    client: TestClient,
    issued_auth_tokens: dict[str, str],
) -> None:
    refresh_token_value = issued_auth_tokens["refresh_token"]

    response = client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.AUTH_PREFIX}/revoke-refresh-token",
        json={"refresh_token_value": refresh_token_value},
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT

    response = client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.AUTH_PREFIX}/refresh-auth-tokens",
        json={"refresh_token_value": refresh_token_value},
    )
    data = response.json()

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    error = data["detail"][0]
    assert error["msg"] == "The provided refresh token is invalid, used, revoked or has expired"
    assert error["type"] == "refresh_token_invalid"


def test_revoke_refresh_token__refresh_token_can_only_be_revoked_once(
    client: TestClient,
    issued_auth_tokens: dict[str, str],
) -> None:
    refresh_token_value = issued_auth_tokens["refresh_token"]

    response = client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.AUTH_PREFIX}/revoke-refresh-token",
        json={"refresh_token_value": refresh_token_value},
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT

    response = client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.AUTH_PREFIX}/revoke-refresh-token",
        json={"refresh_token_value": refresh_token_value},
    )
    data = response.json()

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    error = data["detail"][0]
    assert error["msg"] == "The provided refresh token is invalid, used, revoked or has expired"
    assert error["type"] == "refresh_token_invalid"
