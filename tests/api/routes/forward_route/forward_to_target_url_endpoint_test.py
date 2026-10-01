"""
Tests for the forward to target url endpoint.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
import time_machine
from fastapi import status
from sqlalchemy import select

from lnkr.api.dependencies.header import CLIENT_IP_HEADER, FRONTEND_API_KEY_HEADER, USER_AGENT_HEADER
from lnkr.config.application_settings import application_settings
from lnkr.models import Click, ClickSource

if TYPE_CHECKING:
    from httpx2 import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession


async def test_forward_to_target_url__slug_does_not_exist(client: AsyncClient, slug: str) -> None:
    response = await client.get(url=f"{application_settings.FORWARD_PREFIX}/{slug}")

    assert response.status_code == status.HTTP_404_NOT_FOUND

    data = response.json()
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

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["target_url"] == target_url


@pytest.mark.parametrize(
    ("ip_headers", "expected_ip_address", "expected_country_code"),
    [
        pytest.param({}, None, None, id="missing"),
        pytest.param({CLIENT_IP_HEADER: "8.8.8.8"}, "8.8.8.8", "US", id="public"),
        pytest.param({CLIENT_IP_HEADER: "192.168.1.1"}, None, None, id="private"),
        pytest.param({CLIENT_IP_HEADER: "not-an-ip"}, None, None, id="malformed"),
    ],
)
async def test_forward_to_target_url__click_ip_metadata(
    client: AsyncClient,
    session: AsyncSession,
    slug: str,
    target_url: str,
    frontend_api_key: str,
    ip_headers: dict[str, str],
    expected_ip_address: str | None,
    expected_country_code: str | None,
) -> None:
    await client.post(
        url=application_settings.LINKS_PREFIX,
        json={"slug": slug, "target_url": target_url},
    )
    headers = {FRONTEND_API_KEY_HEADER: frontend_api_key} | ip_headers

    response = await client.get(url=f"{application_settings.FORWARD_PREFIX}/{slug}", headers=headers)

    assert response.status_code == status.HTTP_200_OK

    click = (await session.scalars(select(Click))).one()
    assert click.ip_address == expected_ip_address
    assert click.country_code == expected_country_code


@pytest.mark.usefixtures("geoip_database_unavailable")
async def test_forward_to_target_url__geoip_database_unavailable(
    client: AsyncClient,
    slug: str,
    target_url: str,
    frontend_api_key: str,
    ip_address_public: str,
) -> None:
    await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    await client.get(
        url=f"{application_settings.FORWARD_PREFIX}/{slug}",
        headers={FRONTEND_API_KEY_HEADER: frontend_api_key, CLIENT_IP_HEADER: ip_address_public},
    )

    response = await client.get(url=f"{application_settings.LINKS_PREFIX}/{slug}/clicks")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    clicks = data["items"]
    assert len(clicks) == 1
    assert clicks[0]["ip_address"] == ip_address_public
    assert clicks[0]["country_code"] is None


@pytest.mark.usefixtures("frozen_now")
async def test_forward_to_target_url__click_timestamp_and_user_agent_metadata(
    client: AsyncClient,
    session: AsyncSession,
    slug: str,
    target_url: str,
    frontend_api_key: str,
    user_agent: str,
    now: datetime,
) -> None:
    await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    response = await client.get(
        url=f"{application_settings.FORWARD_PREFIX}/{slug}",
        headers={FRONTEND_API_KEY_HEADER: frontend_api_key, USER_AGENT_HEADER: user_agent},
    )

    assert response.status_code == status.HTTP_200_OK

    click = (await session.scalars(select(Click))).one()
    assert click.timestamp == now
    assert click.browser == "Chrome"
    assert click.operating_system == "Mac OS X"


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


async def test_forward_to_target_url__disabled_link(client: AsyncClient, slug: str, target_url: str) -> None:
    await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )
    await client.patch(
        url=f"{application_settings.LINKS_PREFIX}/{slug}",
        json={"status": "disabled"},
    )

    response = await client.get(url=f"{application_settings.FORWARD_PREFIX}/{slug}")

    assert response.status_code == status.HTTP_410_GONE

    data = response.json()
    error = data["detail"][0]
    assert error["type"] == "link_disabled"


async def test_forward_to_target_url__expired_link(
    client: AsyncClient,
    slug: str,
    target_url: str,
) -> None:
    expires_at = datetime(2026, 1, 1, tzinfo=UTC)
    await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url, "expires_at": expires_at.isoformat()},
    )

    with time_machine.travel(expires_at, tick=False):
        response = await client.get(url=f"{application_settings.FORWARD_PREFIX}/{slug}")

    assert response.status_code == status.HTTP_410_GONE

    data = response.json()
    error = data["detail"][0]
    assert error["type"] == "link_expired"


async def test_forward_to_target_url__password_required(
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

    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    assert response.headers["Cache-Control"] == "no-store"
    data = response.json()
    error = data["detail"][0]
    assert error["msg"] == f"Link with slug '{slug}' requires a password"
    assert error["type"] == "link_password_required"

    # No click recorded.
    response = await client.get(
        url=f"{application_settings.LINKS_PREFIX}/{slug}/clicks",
    )
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["items"] == []


async def test_forward_to_target_url__expired_link_with_extended_expiry(
    client: AsyncClient,
    slug: str,
    target_url: str,
) -> None:
    expires_at = datetime(2026, 1, 1, tzinfo=UTC)
    await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url, "expires_at": expires_at.isoformat()},
    )

    with time_machine.travel(expires_at, tick=False):
        response = await client.get(url=f"{application_settings.FORWARD_PREFIX}/{slug}")
        assert response.status_code == status.HTTP_410_GONE

        await client.patch(
            url=f"{application_settings.LINKS_PREFIX}/{slug}",
            json={"expires_at": (expires_at + timedelta(seconds=1)).isoformat()},
        )

        response = await client.get(url=f"{application_settings.FORWARD_PREFIX}/{slug}")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["target_url"] == target_url
