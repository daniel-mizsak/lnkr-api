"""
Tests for the forward to target url endpoint.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

from typing import TYPE_CHECKING

from fastapi import status

from lnkr.config import settings

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def test_forward_to_target_url__slug_does_not_exist(client: TestClient, slug: str) -> None:
    response = client.get(url=f"{settings.API_VERSION_PREFIX}{settings.FORWARD_PREFIX}/{slug}")
    data = response.json()

    assert response.status_code == status.HTTP_404_NOT_FOUND
    error = data["detail"][0]
    assert error["input"] == slug
    assert error["loc"] == ["path", "slug"]
    assert error["msg"] == f"Slug '{slug}' does not exist"
    assert error["type"] == "slug_does_not_exist"


def test_forward_to_target_url__success(client: TestClient, slug: str, target_url: str) -> None:
    client.post(
        url=f"{settings.API_VERSION_PREFIX}{settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    response = client.get(url=f"{settings.API_VERSION_PREFIX}{settings.FORWARD_PREFIX}/{slug}")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["target_url"] == target_url
