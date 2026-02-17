"""
Tests for the list links endpoint.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

from typing import TYPE_CHECKING

from fastapi import status

from lnkr.config import settings

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def test_list_links__empty(client: TestClient) -> None:
    response = client.get(url=f"{settings.API_VERSION_PREFIX}{settings.LINKS_PREFIX}")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data == []


def test_list_links__success(client: TestClient, slug: str, target_url: str) -> None:
    client.post(
        url=f"{settings.API_VERSION_PREFIX}{settings.LINKS_PREFIX}",
        json={"slug": f"{slug}-1", "target_url": f"{target_url}/1"},
    )
    client.post(
        url=f"{settings.API_VERSION_PREFIX}{settings.LINKS_PREFIX}",
        json={"slug": f"{slug}-2", "target_url": f"{target_url}/2"},
    )

    response = client.get(url=f"{settings.API_VERSION_PREFIX}{settings.LINKS_PREFIX}")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 2
    returned_slugs = {item["slug"] for item in data}
    expected_slugs = {f"{slug}-1", f"{slug}-2"}
    assert returned_slugs == expected_slugs
    returned_targets = {item["target_url"] for item in data}
    expected_targets = {f"{target_url}/1", f"{target_url}/2"}
    assert returned_targets == expected_targets
