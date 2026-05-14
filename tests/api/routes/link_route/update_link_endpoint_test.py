"""
Tests for the update link endpoint.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING

from fastapi import status

from lnkr.config.application_settings import application_settings

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from lnkr.models import User
    from tests.api.conftest import OverrideGetCurrentUserFunction


def test_update_link__invalid_target_url(client: TestClient, slug: str, target_url_invalid: str) -> None:
    response = client.patch(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}/{slug}",
        json={"target_url": target_url_invalid},
    )
    data = response.json()

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    error = data["detail"][0]
    assert error["input"] == target_url_invalid
    assert error["loc"] == ["body", "target_url"]
    assert error["msg"] == "Input should be a valid URL, relative URL without a base"
    assert error["type"] == "url_parsing"


def test_update_link__slug_does_not_exist(client: TestClient, slug: str, target_url: str) -> None:
    response = client.patch(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}/{slug}",
        json={"target_url": target_url},
    )
    data = response.json()

    assert response.status_code == status.HTTP_404_NOT_FOUND
    error = data["detail"][0]
    assert error["input"] == slug
    assert error["loc"] == ["path", "slug"]
    assert error["msg"] == f"Slug '{slug}' does not exist"
    assert error["type"] == "slug_does_not_exist"


def test_update_link__slug_not_owned_by_user(
    client: TestClient,
    override_get_current_user: OverrideGetCurrentUserFunction,
    other_user: User,
    slug: str,
    target_url: str,
) -> None:
    client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    override_get_current_user(other_user)
    response = client.patch(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}/{slug}",
        json={"target_url": f"{target_url}/1"},
    )
    data = response.json()

    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = data["detail"][0]
    assert error["input"] == slug
    assert error["loc"] == ["path", "slug"]
    assert error["msg"] == f"Slug '{slug}' is not owned by the current user"
    assert error["type"] == "slug_not_owned_by_user"


def test_update_link__success(client: TestClient, slug: str, target_url: str) -> None:
    response = client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": f"{target_url}/1"},
    )
    data = response.json()
    original_created_at = data["created_at"]
    original_updated_at = data["updated_at"]

    response = client.patch(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}/{slug}",
        json={"target_url": target_url},
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert set(data.keys()) == {"slug", "target_url", "created_at", "updated_at"}
    assert data["slug"] == slug
    assert data["target_url"] == target_url

    assert data["created_at"] == original_created_at
    assert data["updated_at"] > original_updated_at
