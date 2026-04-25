"""
Tests for the list links endpoint.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING

from fastapi import status

from lnkr.config.application_settings import application_settings

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def test_list_links__empty(client: TestClient) -> None:
    response = client.get(url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data == []


def test_list_links__success(client: TestClient, slug: str, target_url: str) -> None:
    for index in range(1, 3):
        client.post(
            url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
            json={"slug": f"{slug}-{index}", "target_url": f"{target_url}/{index}"},
        )

    response = client.get(url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 2
    returned_slugs = {item["slug"] for item in data}
    expected_slugs = {f"{slug}-1", f"{slug}-2"}
    assert returned_slugs == expected_slugs
    returned_targets = {item["target_url"] for item in data}
    expected_targets = {f"{target_url}/1", f"{target_url}/2"}
    assert returned_targets == expected_targets


def test_list_links__query_parameters(client: TestClient, slug: str, target_url: str) -> None:
    for index in range(1, 6):
        client.post(
            url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
            json={"slug": f"{slug}-{index}", "target_url": f"{target_url}/{index}"},
        )

    response = client.get(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}?sort=created_at&direction=ascending&per_page=2&page=2"
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 2
    returned_slugs = [item["slug"] for item in data]
    expected_slugs = [f"{slug}-3", f"{slug}-4"]
    assert returned_slugs == expected_slugs
