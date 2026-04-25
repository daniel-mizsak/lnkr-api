"""
Tests for the verify login token endpoint.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING

from fastapi import status

from lnkr.config.application_settings import application_settings
from lnkr.services.tokens.access_token_service import decode_access_token

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from lnkr.models import User


def test_verify_login_token_endpoint__login_token_invalid(client: TestClient) -> None:
    response = client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.AUTH_PREFIX}/verify-login-token",
        json={"login_token_value": ""},
    )
    data = response.json()

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    error = data["detail"][0]
    assert error["msg"] == "The provided login token is invalid, used or has expired"
    assert error["type"] == "login_token_invalid"


def test_verify_login_token__success(client: TestClient, issued_login_token: str, user: User) -> None:
    response = client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.AUTH_PREFIX}/verify-login-token",
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


def test_verify_login_token__token_can_only_be_used_once(client: TestClient, issued_login_token: str) -> None:
    response = client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.AUTH_PREFIX}/verify-login-token",
        json={"login_token_value": issued_login_token},
    )
    assert response.status_code == status.HTTP_200_OK

    response = client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.AUTH_PREFIX}/verify-login-token",
        json={"login_token_value": issued_login_token},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    error = response.json()["detail"][0]
    assert error["msg"] == "The provided login token is invalid, used or has expired"
    assert error["type"] == "login_token_invalid"
