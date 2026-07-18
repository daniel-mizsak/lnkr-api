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
    assert data["items"] == []


def test_list_links__success(client: TestClient, slug: str, target_url: str) -> None:
    for index in range(1, 3):
        client.post(
            url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
            json={"slug": f"{slug}-{index}", "target_url": f"{target_url}/{index}"},
        )

    response = client.get(url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data["items"]) == 2
    returned_slugs = {item["slug"] for item in data["items"]}
    expected_slugs = {f"{slug}-1", f"{slug}-2"}
    assert returned_slugs == expected_slugs
    returned_targets = {item["target_url"] for item in data["items"]}
    expected_targets = {f"{target_url}/1", f"{target_url}/2"}
    assert returned_targets == expected_targets


def test_list_links__search_matches_slug_or_target_url(client: TestClient, target_url: str) -> None:
    links = [
        {"slug": "search-slug", "target_url": f"{target_url}unmatched"},
        {"slug": "other-slug", "target_url": f"{target_url}search-target"},
        {"slug": "unrelated", "target_url": f"{target_url}unrelated"},
    ]
    for link in links:
        client.post(
            url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
            json=link,
        )

    response = client.get(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        params={"search": "SEARCH"},
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert {item["slug"] for item in data["items"]} == {"search-slug", "other-slug"}


def test_list_links__search_no_matches(client: TestClient, slug: str, target_url: str) -> None:
    client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    response = client.get(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        params={"search": "missing"},
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["items"] == []


def test_list_links__blank_search(client: TestClient, slug: str, target_url: str) -> None:
    client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    response = client.get(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        params={"search": "   "},
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert [item["slug"] for item in data["items"]] == [slug]


def test_list_links__favorites_only(client: TestClient, slug: str, target_url: str) -> None:
    for index in range(1, 3):
        client.post(
            url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
            json={"slug": f"{slug}-{index}", "target_url": f"{target_url}/{index}"},
        )

    client.patch(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}/{slug}-1",
        json={"favorite": True},
    )

    response = client.get(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        params={"favorites_only": True},
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert [item["slug"] for item in data["items"]] == [f"{slug}-1"]

    response = client.get(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        params={"favorites_only": False},
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert {item["slug"] for item in data["items"]} == {f"{slug}-1", f"{slug}-2"}


def test_list_links__pagination_metadata_uses_filtered_total(client: TestClient, target_url: str) -> None:
    links = [
        {"slug": "matching-1", "target_url": f"{target_url}/1"},
        {"slug": "matching-2", "target_url": f"{target_url}/2"},
        {"slug": "unrelated", "target_url": f"{target_url}/3"},
    ]
    for link in links:
        client.post(
            url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
            json=link,
        )

    response = client.get(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        params={"search": "matching", "per_page": 1},
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["total"] == 2
    assert data["has_next"] is True


def test_list_links__query_parameters(client: TestClient, slug: str, target_url: str) -> None:
    for index in range(1, 6):
        client.post(
            url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
            json={"slug": f"{slug}-{index}", "target_url": f"{target_url}/{index}"},
        )

    response = client.get(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        params={"sort": "created_at", "direction": "ascending", "per_page": 2, "page": 2},
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["total"] == 5
    assert data["page"] == 2
    assert data["per_page"] == 2
    assert data["has_next"] is True
    assert len(data["items"]) == 2
    returned_slugs = [item["slug"] for item in data["items"]]
    expected_slugs = [f"{slug}-3", f"{slug}-4"]
    assert returned_slugs == expected_slugs

    response = client.get(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        params={"sort": "created_at", "direction": "ascending", "per_page": 2, "page": 3},
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert [item["slug"] for item in data["items"]] == [f"{slug}-5"]
    assert data["has_next"] is False
