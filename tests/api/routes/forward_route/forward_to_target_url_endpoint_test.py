"""
Tests for the forward to target url endpoint.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING

from fastapi import status
from sqlalchemy import select

from lnkr.api.dependencies.header import CLIENT_IP_HEADER, FRONTEND_API_KEY_HEADER, USER_AGENT_HEADER
from lnkr.config.application_settings import application_settings
from lnkr.models import Click, ClickSource

if TYPE_CHECKING:
    from datetime import datetime

    from httpx2 import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession


async def test_forward_to_target_url__slug_does_not_exist(client: AsyncClient, slug: str) -> None:
    response = await client.get(url=f"{application_settings.FORWARD_PREFIX}/{slug}")
    data = response.json()

    assert response.status_code == status.HTTP_404_NOT_FOUND
    error = data["detail"][0]
    assert error["input"] == slug
    assert error["loc"] == ["path", "slug"]
    assert error["msg"] == f"Slug '{slug}' does not exist"
    assert error["type"] == "slug_does_not_exist"


async def test_forward_to_target_url__active_link(
    client: AsyncClient,
    slug: str,
    target_url: str,
) -> None:
    await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    response = await client.get(url=f"{application_settings.FORWARD_PREFIX}/{slug}")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["target_url"] == target_url


async def test_forward_to_target_url__click_ip_metadata(
    client: AsyncClient,
    slug: str,
    target_url: str,
    frontend_api_key: str,
    ip_address_public: str,
    ip_address_public_country_code: str,
    ip_address_private: str,
    ip_address_malformed: str,
) -> None:
    frontend_api_key_headers = {FRONTEND_API_KEY_HEADER: frontend_api_key}
    await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    await client.get(url=f"{application_settings.FORWARD_PREFIX}/{slug}", headers=frontend_api_key_headers)
    await client.get(
        url=f"{application_settings.FORWARD_PREFIX}/{slug}",
        headers=frontend_api_key_headers | {CLIENT_IP_HEADER: ip_address_public},
    )
    await client.get(
        url=f"{application_settings.FORWARD_PREFIX}/{slug}",
        headers=frontend_api_key_headers | {CLIENT_IP_HEADER: ip_address_private},
    )
    await client.get(
        url=f"{application_settings.FORWARD_PREFIX}/{slug}",
        headers=frontend_api_key_headers | {CLIENT_IP_HEADER: ip_address_malformed},
    )

    response = await client.get(url=f"{application_settings.LINKS_PREFIX}/{slug}/clicks")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data["items"]) == 4
    # Clicks are returned most recent first: malformed, private, public, then no IP.
    # Only the globally routable address (and its resolved country) is stored.
    assert [item["ip_address"] for item in data["items"]] == [None, None, ip_address_public, None]
    assert [item["country_code"] for item in data["items"]] == [None, None, ip_address_public_country_code, None]


async def test_forward_to_target_url__click_user_agent_metadata(
    client: AsyncClient,
    slug: str,
    target_url: str,
    frontend_api_key: str,
    user_agent: str,
) -> None:
    await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )
    await client.get(
        url=f"{application_settings.FORWARD_PREFIX}/{slug}",
        headers={FRONTEND_API_KEY_HEADER: frontend_api_key, USER_AGENT_HEADER: user_agent},
    )

    response = await client.get(url=f"{application_settings.LINKS_PREFIX}/{slug}/clicks")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["items"]) == 1
    click = data["items"][0]
    assert click["browser"] == "Chrome"
    assert click["operating_system"] == "Mac OS X"


async def test_forward_to_target_url__click_source(
    client: AsyncClient,
    session: AsyncSession,
    slug: str,
    target_url: str,
    frontend_api_key: str,
    frontend_api_key_invalid: str,
) -> None:
    await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    await client.get(url=f"{application_settings.FORWARD_PREFIX}/{slug}")
    await client.get(
        url=f"{application_settings.FORWARD_PREFIX}/{slug}",
        headers={FRONTEND_API_KEY_HEADER: frontend_api_key_invalid},
    )
    await client.get(
        url=f"{application_settings.FORWARD_PREFIX}/{slug}",
        headers={FRONTEND_API_KEY_HEADER: frontend_api_key},
    )

    result = await session.execute(select(Click.source).order_by(Click.timestamp, Click.id))
    click_sources = list(result.scalars())
    assert click_sources == [ClickSource.PUBLIC_API, ClickSource.PUBLIC_API, ClickSource.LNKR_APP]


async def test_forward_to_target_url__disabled(client: AsyncClient, slug: str, target_url: str) -> None:
    await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )
    await client.patch(
        url=f"{application_settings.LINKS_PREFIX}/{slug}",
        json={"status": "disabled"},
    )

    response = await client.get(url=f"{application_settings.FORWARD_PREFIX}/{slug}")
    data = response.json()

    assert response.status_code == status.HTTP_410_GONE
    error = data["detail"][0]
    assert error["type"] == "link_disabled"


async def test_forward_to_target_url__expired(
    client: AsyncClient,
    slug: str,
    target_url: str,
    expires_at_past: datetime,
) -> None:
    await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url, "expires_at": expires_at_past.isoformat()},
    )

    response = await client.get(url=f"{application_settings.FORWARD_PREFIX}/{slug}")
    data = response.json()

    assert response.status_code == status.HTTP_410_GONE
    error = data["detail"][0]
    assert error["type"] == "link_expired"


async def test_forward_to_target_url__password(
    client: AsyncClient,
    slug: str,
    target_url: str,
    password: str,
) -> None:
    await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url, "password": password},
    )

    response = await client.get(url=f"{application_settings.FORWARD_PREFIX}/{slug}")
    data = response.json()

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.headers["Cache-Control"] == "no-store"
    error = data["detail"][0]
    assert error["msg"] == f"Link with slug '{slug}' requires a password"
    assert error["type"] == "link_password_required"

    # No click recorded.
    response = await client.get(
        url=f"{application_settings.LINKS_PREFIX}/{slug}/clicks",
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["items"] == []


async def test_forward_to_target_url__expired_link_with_extended_expiry(
    client: AsyncClient,
    slug: str,
    target_url: str,
    expires_at_past: datetime,
    expires_at_future: datetime,
) -> None:
    await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url, "expires_at": expires_at_past.isoformat()},
    )

    response = await client.get(url=f"{application_settings.FORWARD_PREFIX}/{slug}")
    assert response.status_code == status.HTTP_410_GONE

    await client.patch(
        url=f"{application_settings.LINKS_PREFIX}/{slug}",
        json={"expires_at": expires_at_future.isoformat()},
    )

    response = await client.get(url=f"{application_settings.FORWARD_PREFIX}/{slug}")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["target_url"] == target_url
