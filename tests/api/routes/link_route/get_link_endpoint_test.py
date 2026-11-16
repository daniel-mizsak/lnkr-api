"""
Tests for the get link endpoint.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING

import pytest
from fastapi import status

from lnkr.config.application_settings import application_settings

if TYPE_CHECKING:
    from datetime import datetime

    from httpx2 import AsyncClient

    from lnkr.models import User
    from tests.api.routes.conftest import OverrideGetCurrentUserFunction


async def test_get_link__slug_does_not_exist(client: AsyncClient, slug: str) -> None:
    response = await client.get(url=f"{application_settings.LINKS_PREFIX}/{slug}")

    assert response.status_code == status.HTTP_404_NOT_FOUND

    data = response.json()
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

    assert response.status_code == status.HTTP_403_FORBIDDEN

    data = response.json()
    error = data["detail"][0]

    assert error["input"] == slug
    assert error["loc"] == ["path", "slug"]
    assert error["msg"] == f"Slug '{slug}' is not owned by the current user"
    assert error["type"] == "slug_not_owned_by_user"


@pytest.mark.usefixtures("frozen_now")
async def test_get_link__slug_owned_by_current_user(
    client: AsyncClient,
    slug: str,
    target_url: str,
    now: datetime,
) -> None:
    await client.post(
        url=application_settings.LINKS_PREFIX,
        json={"slug": slug, "target_url": target_url},
    )

    response = await client.get(url=f"{application_settings.LINKS_PREFIX}/{slug}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "slug": slug,
        "target_url": target_url,
        "status": "active",
        "favorite": False,
        "expires_at": None,
        "password_protected": False,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "updated_at": now.isoformat().replace("+00:00", "Z"),
    }
