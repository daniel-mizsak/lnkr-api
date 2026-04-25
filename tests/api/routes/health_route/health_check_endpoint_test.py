"""
Tests for the health check endpoint.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING

from fastapi import status

from lnkr.config.application_settings import ApplicationEnvironment, application_settings

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def test_health_check__success(client: TestClient) -> None:
    response = client.get(url=f"{application_settings.API_VERSION_PREFIX}/health")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["message"] == "lnkr api running"
    assert data["environment"] == ApplicationEnvironment.DEVELOPMENT
    assert data["database"] is True
    assert data["cache"] is True
