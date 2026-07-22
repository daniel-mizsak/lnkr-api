"""
Tests for the create link endpoint.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest import mock

import pytest
from fastapi import status

from lnkr.api.routes import link_route
from lnkr.config.application_settings import application_settings
from lnkr.exceptions import SlugAlreadyExistsError, UserDoesNotExistError, UserLinkLimitExceededError
from lnkr.models.link_model import TARGET_URL_MAX_LENGTH

if TYPE_CHECKING:
    from httpx2 import AsyncClient

    from lnkr.models import User


@pytest.mark.parametrize(
    ("invalid_slug", "expected_type", "expected_message"),
    [
        ("slg", "string_too_short", "String should have at least 4 characters"),
        ("slug" * 5, "string_too_long", "String should have at most 16 characters"),
        ("slug_invalid", "string_pattern_mismatch", "String should match pattern '^[a-zA-Z0-9-]+$'"),
    ],
)
async def test_create_link__invalid_slug(
    client: AsyncClient,
    target_url: str,
    invalid_slug: str,
    expected_type: str,
    expected_message: str,
) -> None:
    response = await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": invalid_slug, "target_url": target_url},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    error = response.json()["detail"][0]
    assert error["input"] == invalid_slug
    assert error["loc"] == ["body", "slug"]
    assert error["msg"] == expected_message
    assert error["type"] == expected_type


async def test_create_link__invalid_target_url(
    client: AsyncClient,
    slug: str,
    target_url_invalid: str,
) -> None:
    response = await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url_invalid},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    error = response.json()["detail"][0]
    assert error["input"] == target_url_invalid
    assert error["loc"] == ["body", "target_url"]
    assert error["msg"] == "Input should be a valid URL, relative URL without a base"
    assert error["type"] == "url_parsing"


async def test_create_link__target_url_too_long(
    client: AsyncClient,
    slug: str,
    target_url: str,
) -> None:
    target_url_too_long = target_url + "a" * TARGET_URL_MAX_LENGTH

    response = await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url_too_long},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    error = response.json()["detail"][0]
    assert error["input"] == target_url_too_long
    assert error["loc"] == ["body", "target_url"]
    assert error["msg"] == (
        f"Value should have at most {TARGET_URL_MAX_LENGTH} items after validation, not {len(target_url_too_long)}"
    )
    assert error["type"] == "too_long"


async def test_create_link__slug_already_exists(
    client: AsyncClient,
    slug: str,
    target_url: str,
) -> None:
    create_link = mock.AsyncMock(side_effect=SlugAlreadyExistsError(slug))
    with mock.patch.object(link_route, "create_link", create_link):
        response = await client.post(
            url=f"{application_settings.LINKS_PREFIX}",
            json={"slug": slug, "target_url": target_url},
        )

    assert response.status_code == status.HTTP_409_CONFLICT
    error = response.json()["detail"][0]
    assert error["input"] == slug
    assert error["loc"] == ["body", "slug"]
    assert error["msg"] == f"Slug '{slug}' already exists"
    assert error["type"] == "slug_already_exists"
    create_link.assert_awaited_once()


async def test_create_link__user_does_not_exist(
    client: AsyncClient,
    user: User,
    slug: str,
    target_url: str,
) -> None:
    create_link = mock.AsyncMock(side_effect=UserDoesNotExistError.by_id(user.id))
    with mock.patch.object(link_route, "create_link", create_link):
        response = await client.post(
            url=f"{application_settings.LINKS_PREFIX}",
            json={"slug": slug, "target_url": target_url},
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    error = response.json()["detail"][0]
    assert error["msg"] == f"User with id '{user.id}' does not exist"
    assert error["type"] == "user_does_not_exist"
    create_link.assert_awaited_once()


async def test_create_link__user_link_limit_exceeded(
    client: AsyncClient,
    user: User,
    slug: str,
    target_url: str,
) -> None:
    create_link = mock.AsyncMock(
        side_effect=UserLinkLimitExceededError(user.email, application_settings.USER_LINK_LIMIT),
    )
    with mock.patch.object(link_route, "create_link", create_link):
        response = await client.post(
            url=f"{application_settings.LINKS_PREFIX}",
            json={"slug": slug, "target_url": target_url},
        )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    error = response.json()["detail"][0]
    assert error["msg"] == f"User '{user.email}' exceeds their link limit of {application_settings.USER_LINK_LIMIT}"
    assert error["type"] == "user_link_limit_exceeded"
    create_link.assert_awaited_once()


async def test_create_link__unknown_field(
    client: AsyncClient,
    slug: str,
    target_url: str,
) -> None:
    response = await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url, "unknown": True},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    error = response.json()["detail"][0]
    assert error["loc"] == ["body", "unknown"]
    assert error["msg"] == "Extra inputs are not permitted"
    assert error["type"] == "extra_forbidden"


async def test_create_link__expiration_and_password(
    client: AsyncClient,
    slug: str,
    target_url: str,
    expires_at_future: datetime,
    password: str,
) -> None:
    response = await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={
            "slug": slug,
            "target_url": target_url,
            "expires_at": expires_at_future.isoformat(),
            "password": password,
        },
    )
    data = response.json()

    assert response.status_code == status.HTTP_201_CREATED
    assert set(data) == {
        "slug",
        "target_url",
        "status",
        "favorite",
        "expires_at",
        "password_protected",
        "created_at",
        "updated_at",
    }
    assert data["slug"] == slug
    assert data["target_url"] == target_url
    assert data["status"] == "active"
    assert data["favorite"] is False
    assert datetime.fromisoformat(data["expires_at"]) == expires_at_future
    assert data["password_protected"] is True

    now = datetime.now(UTC)
    assert now - timedelta(seconds=5) <= datetime.fromisoformat(data["created_at"]) <= now
    assert now - timedelta(seconds=5) <= datetime.fromisoformat(data["updated_at"]) <= now
