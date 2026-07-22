"""
Tests for the get user endpoint.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING

from fastapi import status

from lnkr.config.application_settings import application_settings

if TYPE_CHECKING:
    from httpx2 import AsyncClient


async def test_get_user__authenticated_user(client: AsyncClient) -> None:
    response = await client.get(url=f"{application_settings.USER_PREFIX}")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert set(data.keys()) == {"email", "status"}
    assert data["email"] == "user@example.com"
    assert data["status"] == "regular"
