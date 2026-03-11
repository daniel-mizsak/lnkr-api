"""
Tests for the get user endpoint.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

from typing import TYPE_CHECKING

from fastapi import status

from lnkr.config import settings

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def test_get_user__success(client: TestClient) -> None:
    response = client.get(url=f"{settings.API_VERSION_PREFIX}{settings.USER_PREFIX}")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert set(data.keys()) == {"email", "status"}
    assert data["email"] == "user@example.com"
    assert data["status"] == "regular"
