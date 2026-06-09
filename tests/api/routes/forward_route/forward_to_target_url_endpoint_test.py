"""
Tests for the forward to target url endpoint.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING

import pytest
from fastapi import status

from lnkr.config.application_settings import application_settings

if TYPE_CHECKING:
    from datetime import datetime

    from fastapi.testclient import TestClient


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


def test_forward_to_target_url__click_metadata(
    client: TestClient,
    slug: str,
    target_url: str,
    ip_address_public: str,
    ip_address_public_country_code: str,
    ip_address_private: str,
    ip_address_malformed: str,
) -> None:
    client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    client.get(url=f"{application_settings.API_VERSION_PREFIX}{application_settings.FORWARD_PREFIX}/{slug}")
    client.get(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.FORWARD_PREFIX}/{slug}",
        headers={"X-Client-IP": ip_address_public},
    )
    client.get(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.FORWARD_PREFIX}/{slug}",
        headers={"X-Client-IP": ip_address_private},
    )
    client.get(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.FORWARD_PREFIX}/{slug}",
        headers={"X-Client-IP": ip_address_malformed},
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


@pytest.mark.usefixtures("override_check_frontend_api_key")
def test_forward_to_target_url__ip_address_skipped_when_not_frontend(
    client: TestClient,
    slug: str,
    target_url: str,
) -> None:
    client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    client.get(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.FORWARD_PREFIX}/{slug}",
        headers={"X-Client-IP": "192.168.1.1"},
    )

    response = client.get(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}/{slug}/clicks"
    )
    data = response.json()

    assert len(data) == 1
    assert data[0]["ip_address"] is None


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
