"""
Tests for the create link endpoint.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from fastapi import status

from lnkr.config.application_settings import application_settings
from lnkr.exceptions import UserDoesNotExistError
from lnkr.models.link_model import MAX_TARGET_URL_LENGTH

if TYPE_CHECKING:
    from collections.abc import Generator

    from fastapi.testclient import TestClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from lnkr.models import Link, LinkCreate, User


def test_create_link__invalid_slug(client: TestClient, target_url: str) -> None:
    # min_length
    slug_invalid = "slg"
    response = client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
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
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
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
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        json={"slug": slug_invalid, "target_url": target_url},
    )
    data = response.json()

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    error = data["detail"][0]
    assert error["input"] == slug_invalid
    assert error["loc"] == ["body", "slug"]
    assert error["msg"] == "String should match pattern '^[a-zA-Z0-9-]+$'"
    assert error["type"] == "string_pattern_mismatch"


def test_create_link__invalid_target_url(
    client: TestClient,
    slug: str,
    target_url: str,
    target_url_invalid: str,
) -> None:
    # url_parsing
    response = client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url_invalid},
    )
    data = response.json()

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    error = data["detail"][0]
    assert error["input"] == target_url_invalid
    assert error["loc"] == ["body", "target_url"]
    assert error["msg"] == "Input should be a valid URL, relative URL without a base"
    assert error["type"] == "url_parsing"

    # max_length
    target_url_too_long = target_url + "a" * MAX_TARGET_URL_LENGTH
    response = client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url_too_long},
    )
    data = response.json()

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    error = data["detail"][0]
    assert error["input"] == target_url_too_long
    assert error["loc"] == ["body", "target_url"]
    assert error["msg"] == (
        f"Value should have at most {MAX_TARGET_URL_LENGTH} items after validation, not {len(target_url_too_long)}"
    )
    assert error["type"] == "too_long"


def test_create_link__slug_already_exists(client: TestClient, slug: str, target_url: str) -> None:
    client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    response = client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": f"{target_url}/1"},
    )
    data = response.json()

    assert response.status_code == status.HTTP_409_CONFLICT
    error = data["detail"][0]
    assert error["input"] == slug
    assert error["loc"] == ["body", "slug"]
    assert error["msg"] == f"Slug '{slug}' already exists"
    assert error["type"] == "slug_already_exists"


def test_create_link__user_does_not_exist(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    user: User,
    slug: str,
    target_url: str,
) -> None:
    async def _create_link(_session: AsyncSession, _link_create: LinkCreate, user: User) -> Link:
        raise UserDoesNotExistError.by_id(user_id=user.id)

    monkeypatch.setattr("lnkr.api.routes.link_route.create_link", _create_link)

    response = client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )
    data = response.json()

    assert response.status_code == status.HTTP_404_NOT_FOUND
    error = data["detail"][0]
    assert error["msg"] == f"User with id '{user.id}' does not exist"
    assert error["type"] == "user_does_not_exist"


@pytest.mark.usefixtures("_override_user_link_limit")
def test_create_link__user_link_limit_exceeded(client: TestClient, email: str, slug: str, target_url: str) -> None:
    client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        json={"slug": f"{slug}-1", "target_url": f"{target_url}/1"},
    )
    response = client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        json={"slug": f"{slug}-2", "target_url": f"{target_url}/2"},
    )
    data = response.json()

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    error = data["detail"][0]
    assert error["msg"] == f"User '{email}' exceeds their link limit of 1"
    assert error["type"] == "user_link_limit_exceeded"


@pytest.fixture
def _override_user_link_limit() -> Generator[None]:
    original_limit = application_settings.USER_LINK_LIMIT
    application_settings.USER_LINK_LIMIT = 1
    yield
    application_settings.USER_LINK_LIMIT = original_limit


def test_create_link__unknown_field_rejected(
    client: TestClient,
    slug: str,
    target_url: str,
    expires_at_future: datetime,
) -> None:
    response = client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url, "expires_a": expires_at_future.isoformat()},
    )
    data = response.json()

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    error = data["detail"][0]
    assert error["loc"] == ["body", "expires_a"]
    assert error["msg"] == "Extra inputs are not permitted"
    assert error["type"] == "extra_forbidden"


def test_create_link__expires_at_not_set(client: TestClient, slug: str, target_url: str) -> None:
    response = client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )
    data = response.json()

    assert response.status_code == status.HTTP_201_CREATED
    assert data["expires_at"] is None


def test_create_link__password_not_set(client: TestClient, slug: str, target_url: str) -> None:
    response = client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )
    data = response.json()

    assert response.status_code == status.HTTP_201_CREATED
    assert data["password_protected"] is False


def test_create_link__success(
    client: TestClient,
    slug: str,
    target_url: str,
    expires_at_future: datetime,
    password: str,
) -> None:
    response = client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        json={
            "slug": slug,
            "target_url": target_url,
            "expires_at": expires_at_future.isoformat(),
            "password": password,
        },
    )
    data = response.json()

    assert response.status_code == status.HTTP_201_CREATED
    assert set(data.keys()) == {
        "slug",
        "target_url",
        "status",
        "expires_at",
        "password_protected",
        "created_at",
        "updated_at",
    }
    assert data["slug"] == slug
    assert data["target_url"] == target_url
    assert data["status"] == "active"
    assert datetime.fromisoformat(data["expires_at"]) == expires_at_future
    assert data["password_protected"] is True

    now = datetime.now(UTC)
    created_at = datetime.fromisoformat(data["created_at"])
    updated_at = datetime.fromisoformat(data["updated_at"])

    assert now - timedelta(seconds=5) <= created_at <= now
    assert now - timedelta(seconds=5) <= updated_at <= now
