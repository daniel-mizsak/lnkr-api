"""
Tests for the create link endpoint.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

from typing import TYPE_CHECKING

import pytest
from fastapi import status

from lnkr.config import settings

if TYPE_CHECKING:
    from collections.abc import Generator

    from fastapi.testclient import TestClient

    from lnkr.models import User


@pytest.fixture
def _override_user_link_limit() -> Generator[None]:
    original_limit = settings.USER_LINK_LIMIT
    settings.USER_LINK_LIMIT = 1
    yield
    settings.USER_LINK_LIMIT = original_limit


def test_create_link__invalid_slug(client: TestClient, target_url: str) -> None:
    # min_length
    slug_invalid = "slg"
    response = client.post(
        url=f"{settings.API_VERSION_PREFIX}{settings.LINKS_PREFIX}",
        json={"slug": slug_invalid, "target_url": target_url},
    )
    data = response.json()

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    error = data["detail"][0]
    assert error["input"] == slug_invalid
    assert error["loc"] == ["body", "slug"]
    assert error["msg"] == "String should have at least 4 characters"
    assert error["type"] == "string_too_short"

    # max_length
    slug_invalid = "slug" * 5
    response = client.post(
        url=f"{settings.API_VERSION_PREFIX}{settings.LINKS_PREFIX}",
        json={"slug": slug_invalid, "target_url": target_url},
    )
    data = response.json()

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    error = data["detail"][0]
    assert error["input"] == slug_invalid
    assert error["loc"] == ["body", "slug"]
    assert error["msg"] == "String should have at most 16 characters"
    assert error["type"] == "string_too_long"

    # pattern
    slug_invalid = "slug_invalid"
    response = client.post(
        url=f"{settings.API_VERSION_PREFIX}{settings.LINKS_PREFIX}",
        json={"slug": slug_invalid, "target_url": target_url},
    )
    data = response.json()

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    error = data["detail"][0]
    assert error["input"] == slug_invalid
    assert error["loc"] == ["body", "slug"]
    assert error["msg"] == "String should match pattern '^[a-zA-Z0-9-]+$'"
    assert error["type"] == "string_pattern_mismatch"


def test_create_link__invalid_target_url(client: TestClient, slug: str, target_url_invalid: str) -> None:
    response = client.post(
        url=f"{settings.API_VERSION_PREFIX}{settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url_invalid},
    )
    data = response.json()

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    error = data["detail"][0]
    assert error["input"] == target_url_invalid
    assert error["loc"] == ["body", "target_url"]
    assert error["msg"] == "Input should be a valid URL, relative URL without a base"
    assert error["type"] == "url_parsing"


def test_create_link__slug_already_exists(client: TestClient, slug: str, target_url: str) -> None:
    client.post(
        url=f"{settings.API_VERSION_PREFIX}{settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    response = client.post(
        url=f"{settings.API_VERSION_PREFIX}{settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": f"{target_url}/1"},
    )
    data = response.json()

    assert response.status_code == status.HTTP_409_CONFLICT
    error = data["detail"][0]
    assert error["input"] == slug
    assert error["loc"] == ["body", "slug"]
    assert error["msg"] == f"Slug '{slug}' already exists"
    assert error["type"] == "slug_already_exists"


@pytest.mark.usefixtures("_override_user_link_limit")
def test_create_link__user_link_limit_exceeded(client: TestClient, user: User, slug: str, target_url: str) -> None:
    client.post(
        url=f"{settings.API_VERSION_PREFIX}{settings.LINKS_PREFIX}",
        json={"slug": f"{slug}-1", "target_url": f"{target_url}/1"},
    )
    response = client.post(
        url=f"{settings.API_VERSION_PREFIX}{settings.LINKS_PREFIX}",
        json={"slug": f"{slug}-2", "target_url": f"{target_url}/2"},
    )
    data = response.json()

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    error = data["detail"][0]
    assert error["msg"] == f"User '{user.email}' exceeds their link limit of 1"
    assert error["type"] == "user_link_limit_exceeded"


def test_create_link__success(client: TestClient, slug: str, target_url: str) -> None:
    response = client.post(
        url=f"{settings.API_VERSION_PREFIX}{settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )
    data = response.json()

    assert response.status_code == status.HTTP_201_CREATED
    assert set(data.keys()) == {"slug", "target_url"}
    assert data["slug"] == slug
    assert data["target_url"] == target_url
