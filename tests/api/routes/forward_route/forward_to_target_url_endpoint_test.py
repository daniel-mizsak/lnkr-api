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

    from fastapi.testclient import TestClient
    from sqlalchemy.ext.asyncio import AsyncSession


def test_forward_to_target_url__slug_does_not_exist(client: TestClient, slug: str) -> None:
    response = client.get(url=f"{application_settings.API_VERSION_PREFIX}{application_settings.FORWARD_PREFIX}/{slug}")
    data = response.json()

    assert response.status_code == status.HTTP_404_NOT_FOUND
    error = data["detail"][0]
    assert error["input"] == slug
    assert error["loc"] == ["path", "slug"]
    assert error["msg"] == f"Slug '{slug}' does not exist"
    assert error["type"] == "slug_does_not_exist"


def test_forward_to_target_url__success(
    client: TestClient,
    slug: str,
    target_url: str,
) -> None:
    client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    response = client.get(url=f"{application_settings.API_VERSION_PREFIX}{application_settings.FORWARD_PREFIX}/{slug}")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["target_url"] == target_url


def test_forward_to_target_url__click_ip_metadata(
    client: TestClient,
    slug: str,
    target_url: str,
    frontend_api_key: str,
    ip_address_public: str,
    ip_address_public_country_code: str,
    ip_address_private: str,
    ip_address_malformed: str,
) -> None:
    frontend_api_key_headers = {FRONTEND_API_KEY_HEADER: frontend_api_key}
    client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    forward_url = f"{application_settings.API_VERSION_PREFIX}{application_settings.FORWARD_PREFIX}/{slug}"
    client.get(url=forward_url, headers=frontend_api_key_headers)
    client.get(
        url=forward_url,
        headers=frontend_api_key_headers | {CLIENT_IP_HEADER: ip_address_public},
    )
    client.get(
        url=forward_url,
        headers=frontend_api_key_headers | {CLIENT_IP_HEADER: ip_address_private},
    )
    client.get(
        url=forward_url,
        headers=frontend_api_key_headers | {CLIENT_IP_HEADER: ip_address_malformed},
    )

    response = client.get(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}/{slug}/clicks"
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 4
    # Clicks are returned most recent first: malformed, private, public, then no IP.
    # Only the globally routable address (and its resolved country) is stored.
    assert [item["ip_address"] for item in data] == [None, None, ip_address_public, None]
    assert [item["country_code"] for item in data] == [None, None, ip_address_public_country_code, None]


def test_forward_to_target_url__click_user_agent_metadata(
    client: TestClient,
    slug: str,
    target_url: str,
    frontend_api_key: str,
    user_agent: str,
) -> None:
    client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )
    client.get(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.FORWARD_PREFIX}/{slug}",
        headers={FRONTEND_API_KEY_HEADER: frontend_api_key, USER_AGENT_HEADER: user_agent},
    )

    response = client.get(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}/{slug}/clicks"
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 1
    click = data[0]
    assert click["browser"] == "Chrome"
    assert click["operating_system"] == "Mac OS X"


async def test_forward_to_target_url__click_source(
    client: TestClient,
    session: AsyncSession,
    slug: str,
    target_url: str,
    frontend_api_key: str,
    frontend_api_key_invalid: str,
) -> None:
    client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    client.get(url=f"{application_settings.API_VERSION_PREFIX}{application_settings.FORWARD_PREFIX}/{slug}")
    client.get(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.FORWARD_PREFIX}/{slug}",
        headers={FRONTEND_API_KEY_HEADER: frontend_api_key_invalid},
    )
    client.get(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.FORWARD_PREFIX}/{slug}",
        headers={FRONTEND_API_KEY_HEADER: frontend_api_key},
    )

    result = await session.execute(select(Click.source).order_by(Click.timestamp, Click.id))
    click_sources = list(result.scalars())
    assert click_sources == [ClickSource.PUBLIC_API, ClickSource.PUBLIC_API, ClickSource.LNKR_APP]


def test_forward_to_target_url__disabled(client: TestClient, slug: str, target_url: str) -> None:
    client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )
    client.patch(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}/{slug}",
        json={"status": "disabled"},
    )

    response = client.get(url=f"{application_settings.API_VERSION_PREFIX}{application_settings.FORWARD_PREFIX}/{slug}")
    data = response.json()

    assert response.status_code == status.HTTP_410_GONE
    error = data["detail"][0]
    assert error["type"] == "link_disabled"


def test_forward_to_target_url__expired(
    client: TestClient,
    slug: str,
    target_url: str,
    expires_at_past: datetime,
) -> None:
    client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url, "expires_at": expires_at_past.isoformat()},
    )

    response = client.get(url=f"{application_settings.API_VERSION_PREFIX}{application_settings.FORWARD_PREFIX}/{slug}")
    data = response.json()

    assert response.status_code == status.HTTP_410_GONE
    error = data["detail"][0]
    assert error["type"] == "link_expired"


def test_forward_to_target_url__password(
    client: TestClient,
    slug: str,
    target_url: str,
    password: str,
) -> None:
    client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url, "password": password},
    )

    response = client.get(url=f"{application_settings.API_VERSION_PREFIX}{application_settings.FORWARD_PREFIX}/{slug}")
    data = response.json()

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.headers["Cache-Control"] == "no-store"
    error = data["detail"][0]
    assert error["msg"] == f"Link with slug '{slug}' requires a password"
    assert error["type"] == "link_password_required"

    # No click recorded.
    response = client.get(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}/{slug}/clicks",
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_forward_to_target_url__extending_expiry_revives_link(
    client: TestClient,
    slug: str,
    target_url: str,
    expires_at_past: datetime,
    expires_at_future: datetime,
) -> None:
    client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url, "expires_at": expires_at_past.isoformat()},
    )

    response = client.get(url=f"{application_settings.API_VERSION_PREFIX}{application_settings.FORWARD_PREFIX}/{slug}")
    assert response.status_code == status.HTTP_410_GONE

    client.patch(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}/{slug}",
        json={"expires_at": expires_at_future.isoformat()},
    )

    response = client.get(url=f"{application_settings.API_VERSION_PREFIX}{application_settings.FORWARD_PREFIX}/{slug}")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["target_url"] == target_url
