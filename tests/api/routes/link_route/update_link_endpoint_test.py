"""
Tests for the update link endpoint.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

from typing import TYPE_CHECKING

from fastapi import status

from lnkr.config import settings

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from lnkr.models import User
    from tests.api.routes.conftest import OverrideUserFunction


def test_update_link__invalid_target_url(client: TestClient, slug: str, target_url_invalid: str) -> None:
    response = client.patch(
        url=f"{settings.API_VERSION_PREFIX}{settings.LINKS_PREFIX}/{slug}",
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
        url=f"{settings.API_VERSION_PREFIX}{settings.LINKS_PREFIX}/{slug}",
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
    response = client.patch(
        url=f"{settings.API_VERSION_PREFIX}{settings.LINKS_PREFIX}/{slug}",
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
    client.post(
        url=f"{settings.API_VERSION_PREFIX}{settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": f"{target_url}/1"},
    )

    response = client.patch(
        url=f"{settings.API_VERSION_PREFIX}{settings.LINKS_PREFIX}/{slug}",
        json={"target_url": target_url},
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert set(data.keys()) == {"slug", "target_url"}
    assert data["slug"] == slug
    assert data["target_url"] == target_url
