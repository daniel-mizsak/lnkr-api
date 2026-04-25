"""
Tests for the refresh auth tokens endpoint.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING

from fastapi import status

from lnkr.config.application_settings import application_settings
from lnkr.services.tokens.access_token_service import decode_access_token

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from lnkr.models import User


def test_refresh_auth_tokens__refresh_token_invalid(client: TestClient) -> None:
    response = client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.AUTH_PREFIX}/refresh-auth-tokens",
        json={"refresh_token_value": ""},
    )
    data = response.json()

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    error = data["detail"][0]
    assert error["msg"] == "The provided refresh token is invalid, used, revoked or has expired"
    assert error["type"] == "refresh_token_invalid"


def test_refresh_auth_tokens__success(client: TestClient, issued_auth_tokens: dict[str, str], user: User) -> None:
    original_refresh_token = issued_auth_tokens["refresh_token"]

    response = client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.AUTH_PREFIX}/refresh-auth-tokens",
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


def test_refresh_auth_tokens__old_refresh_token_can_only_be_used_once(
    client: TestClient,
    issued_auth_tokens: dict[str, str],
) -> None:
    original_refresh_token = issued_auth_tokens["refresh_token"]

    response = client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.AUTH_PREFIX}/refresh-auth-tokens",
        json={"refresh_token_value": original_refresh_token},
    )
    assert response.status_code == status.HTTP_200_OK

    response = client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.AUTH_PREFIX}/refresh-auth-tokens",
        json={"refresh_token_value": original_refresh_token},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    error = response.json()["detail"][0]
    assert error["msg"] == "The provided refresh token is invalid, used, revoked or has expired"
    assert error["type"] == "refresh_token_invalid"


def test_refresh_auth_tokens__new_refresh_token_can_be_used_again(
    client: TestClient,
    issued_auth_tokens: dict[str, str],
) -> None:
    original_refresh_token = issued_auth_tokens["refresh_token"]

    response = client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.AUTH_PREFIX}/refresh-auth-tokens",
        json={"refresh_token_value": original_refresh_token},
    )
    assert response.status_code == status.HTTP_200_OK
    rotated_refresh_token = response.json()["refresh_token"]

    response = client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.AUTH_PREFIX}/refresh-auth-tokens",
        json={"refresh_token_value": rotated_refresh_token},
    )
    assert response.status_code == status.HTTP_200_OK
