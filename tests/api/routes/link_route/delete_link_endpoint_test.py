"""
Tests for the delete link endpoint.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

from typing import TYPE_CHECKING

from fastapi import status

from lnkr.config import settings

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from lnkr.models import User
    from tests.api.routes.conftest import OverrideUserFunction


def test_delete_link__slug_does_not_exists(client: TestClient, slug: str) -> None:
    response = client.delete(url=f"{settings.API_VERSION_PREFIX}{settings.LINKS_PREFIX}/{slug}")
    data = response.json()

    assert response.status_code == status.HTTP_404_NOT_FOUND
    error = data["detail"][0]
    assert error["input"] == slug
    assert error["loc"] == ["path", "slug"]
    assert error["msg"] == f"Slug '{slug}' does not exist"
    assert error["type"] == "slug_does_not_exist"


def test_delete_link__slug_not_owned_by_user(
    client: TestClient,
    override_current_user: OverrideUserFunction,
    other_user: User,
    slug: str,
    target_url: str,
) -> None:
    client.post(
        url=f"{settings.API_VERSION_PREFIX}{settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    override_current_user(other_user)
    response = client.delete(url=f"{settings.API_VERSION_PREFIX}{settings.LINKS_PREFIX}/{slug}")
    data = response.json()

    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = data["detail"][0]
    assert error["input"] == slug
    assert error["loc"] == ["path", "slug"]
    assert error["msg"] == f"Slug '{slug}' is not owned by the current user"
    assert error["type"] == "slug_not_owned_by_user"


def test_delete_link__success(client: TestClient, slug: str, target_url: str) -> None:
    client.post(
        url=f"{settings.API_VERSION_PREFIX}{settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    response = client.delete(url=f"{settings.API_VERSION_PREFIX}{settings.LINKS_PREFIX}/{slug}")

    assert response.status_code == status.HTTP_204_NO_CONTENT

    response = client.get(url=f"{settings.API_VERSION_PREFIX}{settings.LINKS_PREFIX}/{slug}")
    data = response.json()

    assert response.status_code == status.HTTP_404_NOT_FOUND
    error = data["detail"][0]
    assert error["input"] == slug
    assert error["loc"] == ["path", "slug"]
    assert error["msg"] == f"Slug '{slug}' does not exist"
    assert error["type"] == "slug_does_not_exist"


def test_delete_link__reset_click_count(client: TestClient, slug: str, target_url: str) -> None:
    client.post(
        url=f"{settings.API_VERSION_PREFIX}{settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )
    client.get(url=f"{settings.API_VERSION_PREFIX}{settings.FORWARD_PREFIX}/{slug}")
    client.get(url=f"{settings.API_VERSION_PREFIX}{settings.FORWARD_PREFIX}/{slug}")

    response = client.get(url=f"{settings.API_VERSION_PREFIX}{settings.LINKS_PREFIX}/{slug}/clicks")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 2

    client.delete(url=f"{settings.API_VERSION_PREFIX}{settings.LINKS_PREFIX}/{slug}")
    client.post(
        url=f"{settings.API_VERSION_PREFIX}{settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": f"{target_url}/1"},
    )

    response = client.get(url=f"{settings.API_VERSION_PREFIX}{settings.LINKS_PREFIX}/{slug}/clicks")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 0
