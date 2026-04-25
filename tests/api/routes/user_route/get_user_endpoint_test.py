"""
Tests for the get user endpoint.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING

from fastapi import status

from lnkr.config.application_settings import application_settings

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def test_get_user__success(client: TestClient) -> None:
    response = client.get(url=f"{application_settings.API_VERSION_PREFIX}{application_settings.USER_PREFIX}")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert set(data.keys()) == {"email", "status"}
    assert data["email"] == "user@example.com"
    assert data["status"] == "regular"
