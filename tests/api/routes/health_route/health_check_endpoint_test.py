"""
Tests for the health check endpoint.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING

from fastapi import status

from lnkr.config.application_settings import ApplicationEnvironment

if TYPE_CHECKING:
    from httpx2 import AsyncClient


async def test_health_check__healthy_dependencies(client: AsyncClient) -> None:
    response = await client.get(url="/health")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["message"] == "lnkr api running"
    assert data["environment"] == ApplicationEnvironment.DEVELOPMENT
    assert data["database"] is True
    assert data["cache"] is True
