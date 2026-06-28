"""
Tests for the list clicks endpoint.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from fastapi import status

from lnkr.api.dependencies.header import CLIENT_IP_HEADER, FRONTEND_API_KEY_HEADER, USER_AGENT_HEADER
from lnkr.config.application_settings import application_settings

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from lnkr.models import User
    from tests.api.conftest import OverrideGetCurrentUserFunction


def test_list_clicks__slug_does_not_exist(client: TestClient, slug: str) -> None:
    response = client.get(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}/{slug}/clicks"
    )
    data = response.json()

    assert response.status_code == status.HTTP_404_NOT_FOUND
    error = data["detail"][0]
    assert error["input"] == slug
    assert error["loc"] == ["path", "slug"]
    assert error["msg"] == f"Slug '{slug}' does not exist"
    assert error["type"] == "slug_does_not_exist"


def test_list_clicks__slug_not_owned_by_user(
    client: TestClient,
    override_get_current_user: OverrideGetCurrentUserFunction,
    user_other: User,
    slug: str,
    target_url: str,
) -> None:
    client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    override_get_current_user(user_other)
    response = client.get(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}/{slug}/clicks"
    )
    data = response.json()

    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = data["detail"][0]
    assert error["input"] == slug
    assert error["loc"] == ["path", "slug"]
    assert error["msg"] == f"Slug '{slug}' is not owned by the current user"
    assert error["type"] == "slug_not_owned_by_user"


def test_list_clicks__empty(client: TestClient, slug: str, target_url: str) -> None:
    client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    response = client.get(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}/{slug}/clicks"
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data == []


def test_list_clicks__public_api_clicks_excluded(client: TestClient, slug: str, target_url: str) -> None:
    client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )
    client.get(url=f"{application_settings.API_VERSION_PREFIX}{application_settings.FORWARD_PREFIX}/{slug}")

    response = client.get(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}/{slug}/clicks"
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data == []


def test_list_clicks__success(
    client: TestClient,
    slug: str,
    target_url: str,
    frontend_api_key: str,
    ip_address_public: str,
    ip_address_public_country_code: str,
    user_agent: str,
) -> None:
    timestamp = datetime.now(tz=UTC)
    client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    client.get(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.FORWARD_PREFIX}/{slug}",
        headers={FRONTEND_API_KEY_HEADER: frontend_api_key},
    )
    client.get(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.FORWARD_PREFIX}/{slug}",
        headers={
            FRONTEND_API_KEY_HEADER: frontend_api_key,
            CLIENT_IP_HEADER: ip_address_public,
            USER_AGENT_HEADER: user_agent,
        },
    )

    response = client.get(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}/{slug}/clicks"
    )
    data = response.json()

    timestamps = [item["timestamp"] for item in data]
    assert timestamps == sorted(timestamps, reverse=True)
    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 2
    for item in data:
        item_timestamp = datetime.fromisoformat(item["timestamp"])
        assert timestamp < item_timestamp < timestamp + timedelta(seconds=1)
        assert set(item.keys()) == {
            "timestamp",
            "ip_address",
            "country_code",
            "browser",
            "operating_system",
        }
    assert {item["ip_address"] for item in data} == {None, ip_address_public}
    assert {item["country_code"] for item in data} == {None, ip_address_public_country_code}
    assert {item["browser"] for item in data} == {None, "Chrome"}
    assert {item["operating_system"] for item in data} == {None, "Mac OS X"}
