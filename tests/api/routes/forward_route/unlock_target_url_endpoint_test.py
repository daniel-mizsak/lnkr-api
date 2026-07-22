"""
Tests for the unlock target url endpoint.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING

from fastapi import status

from lnkr.api.dependencies.header import FRONTEND_API_KEY_HEADER
from lnkr.config.application_settings import application_settings

if TYPE_CHECKING:
    from datetime import datetime

    from httpx2 import AsyncClient


async def test_unlock_target_url__slug_does_not_exist(client: AsyncClient, slug: str, password: str) -> None:
    response = await client.post(
        url=f"{application_settings.FORWARD_PREFIX}/{slug}/unlock",
        json={"password": password},
    )
    data = response.json()

    assert response.status_code == status.HTTP_404_NOT_FOUND
    error = data["detail"][0]
    assert error["input"] == slug
    assert error["loc"] == ["path", "slug"]
    assert error["msg"] == f"Slug '{slug}' does not exist"
    assert error["type"] == "slug_does_not_exist"


async def test_unlock_target_url__missing_password(
    client: AsyncClient,
    slug: str,
    target_url: str,
    password: str,
) -> None:
    await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url, "password": password},
    )

    response = await client.post(
        url=f"{application_settings.FORWARD_PREFIX}/{slug}/unlock",
        json={},
    )
    data = response.json()

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    error = data["detail"][0]
    assert error["loc"] == ["body", "password"]
    assert error["msg"] == "Field required"
    assert error["type"] == "missing"


async def test_unlock_target_url__empty_password(
    client: AsyncClient,
    slug: str,
    target_url: str,
    password: str,
) -> None:
    await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url, "password": password},
    )

    response = await client.post(
        url=f"{application_settings.FORWARD_PREFIX}/{slug}/unlock",
        json={"password": ""},
    )
    data = response.json()

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    error = data["detail"][0]
    assert error["loc"] == ["body", "password"]
    assert error["msg"] == "String should have at least 1 character"
    assert error["type"] == "string_too_short"


async def test_unlock_target_url__wrong_password(
    client: AsyncClient,
    slug: str,
    target_url: str,
    password: str,
) -> None:
    await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url, "password": password},
    )

    response = await client.post(
        url=f"{application_settings.FORWARD_PREFIX}/{slug}/unlock",
        json={"password": f"wrong-{password}"},
    )
    data = response.json()

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.headers["Cache-Control"] == "no-store"
    error = data["detail"][0]
    assert error["msg"] == f"The provided password for link with slug '{slug}' is invalid"
    assert error["type"] == "link_password_invalid"

    # No click recorded.
    response = await client.get(
        url=f"{application_settings.LINKS_PREFIX}/{slug}/clicks",
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["items"] == []


async def test_unlock_target_url__matching_password(
    client: AsyncClient,
    slug: str,
    target_url: str,
    password: str,
    frontend_api_key: str,
) -> None:
    await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url, "password": password},
    )

    response = await client.post(
        url=f"{application_settings.FORWARD_PREFIX}/{slug}/unlock",
        json={"password": password},
        headers={FRONTEND_API_KEY_HEADER: frontend_api_key},
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["target_url"] == target_url

    # Click recorded.
    response = await client.get(
        url=f"{application_settings.LINKS_PREFIX}/{slug}/clicks",
    )
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()["items"]) == 1


async def test_unlock_target_url__link_without_password(
    client: AsyncClient,
    slug: str,
    target_url: str,
    password: str,
) -> None:
    await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    response = await client.post(
        url=f"{application_settings.FORWARD_PREFIX}/{slug}/unlock",
        json={"password": password},
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["target_url"] == target_url


async def test_unlock_target_url__disabled(client: AsyncClient, slug: str, target_url: str, password: str) -> None:
    await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url, "password": password},
    )
    await client.patch(
        url=f"{application_settings.LINKS_PREFIX}/{slug}",
        json={"status": "disabled"},
    )

    response = await client.post(
        url=f"{application_settings.FORWARD_PREFIX}/{slug}/unlock",
        json={"password": password},
    )
    data = response.json()

    assert response.status_code == status.HTTP_410_GONE
    error = data["detail"][0]
    assert error["type"] == "link_disabled"


async def test_unlock_target_url__expired(
    client: AsyncClient,
    slug: str,
    target_url: str,
    password: str,
    expires_at_past: datetime,
) -> None:
    await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={
            "slug": slug,
            "target_url": target_url,
            "password": password,
            "expires_at": expires_at_past.isoformat(),
        },
    )

    response = await client.post(
        url=f"{application_settings.FORWARD_PREFIX}/{slug}/unlock",
        json={"password": password},
    )
    data = response.json()

    assert response.status_code == status.HTTP_410_GONE
    error = data["detail"][0]
    assert error["type"] == "link_expired"
