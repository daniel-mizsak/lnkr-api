"""
Tests for the verify login token endpoint.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

from typing import TYPE_CHECKING

from fastapi import status

from lnkr.config import settings

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def test_verify_login_token_endpoint__login_token_invalid(client: TestClient) -> None:
    response = client.get(
        url=f"{settings.API_VERSION_PREFIX}{settings.AUTH_PREFIX}/verify-login-token",
        params={"login_token_value": ""},
    )
    data = response.json()

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    error = data["detail"][0]
    assert error["msg"] == "The provided login token is invalid or has expired"
    assert error["type"] == "login_token_invalid"
