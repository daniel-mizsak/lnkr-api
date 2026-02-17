"""
Tests for the health check endpoint.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

from typing import TYPE_CHECKING

from fastapi import status

from lnkr.config import Environment, settings

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def test_health_check__success(client: TestClient) -> None:
    response = client.get(url=f"{settings.API_VERSION_PREFIX}/health")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["message"] == "lnkr api running"
    assert data["environment"] == Environment.DEVELOPMENT
    assert data["database"] is True
    assert data["cache"] is True
