"""
Tests for the get link endpoint.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from fastapi import status

from lnkr.config.application_settings import application_settings

if TYPE_CHECKING:
    from httpx2 import AsyncClient

    from lnkr.models import User
    from tests.api.routes.conftest import OverrideGetCurrentUserFunction


async def test_get_link__slug_does_not_exist(client: AsyncClient, slug: str) -> None:
    response = await client.get(url=f"{application_settings.LINKS_PREFIX}/{slug}")
    data = response.json()

    assert response.status_code == status.HTTP_404_NOT_FOUND
    error = data["detail"][0]
    assert error["input"] == slug
    assert error["loc"] == ["path", "slug"]
    assert error["msg"] == f"Slug '{slug}' does not exist"
    assert error["type"] == "slug_does_not_exist"


async def test_get_link__slug_not_owned_by_user(
    client: AsyncClient,
    override_get_current_user: OverrideGetCurrentUserFunction,
    user_other: User,
    slug: str,
    target_url: str,
) -> None:
    await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    override_get_current_user(user_other)
    response = await client.get(url=f"{application_settings.LINKS_PREFIX}/{slug}")
    data = response.json()

    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = data["detail"][0]
    assert error["input"] == slug
    assert error["loc"] == ["path", "slug"]
    assert error["msg"] == f"Slug '{slug}' is not owned by the current user"
    assert error["type"] == "slug_not_owned_by_user"


async def test_get_link__slug_owned_by_current_user(client: AsyncClient, slug: str, target_url: str) -> None:
    await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    response = await client.get(url=f"{application_settings.LINKS_PREFIX}/{slug}")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert set(data.keys()) == {
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
    assert data["expires_at"] is None

    now = datetime.now(UTC)
    created_at = datetime.fromisoformat(data["created_at"])
    updated_at = datetime.fromisoformat(data["updated_at"])

    assert now - timedelta(seconds=5) <= created_at <= now
    assert now - timedelta(seconds=5) <= updated_at <= now
