"""
Tests for the list clicks endpoint.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from fastapi import status

from lnkr.config import settings

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from lnkr.models import User
    from tests.api.routes.conftest import OverrideUserFunction


def test_list_clicks__slug_does_not_exist(client: TestClient, slug: str) -> None:
    response = client.get(url=f"{settings.API_VERSION_PREFIX}{settings.LINKS_PREFIX}/{slug}/clicks")
    data = response.json()

    assert response.status_code == status.HTTP_404_NOT_FOUND
    error = data["detail"][0]
    assert error["input"] == slug
    assert error["loc"] == ["path", "slug"]
    assert error["msg"] == f"Slug '{slug}' does not exist"
    assert error["type"] == "slug_does_not_exist"


def test_list_clicks__slug_not_owned_by_user(
    client: TestClient,
    override_current_user: OverrideUserFunction,
    other_user: User,
    slug: str,
    target_url: str,
) -> None:
    client.post(
        url=f"{settings.API_VERSION_PREFIX}{settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    override_current_user(other_user)
    response = client.get(url=f"{settings.API_VERSION_PREFIX}{settings.LINKS_PREFIX}/{slug}/clicks")
    data = response.json()

    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = data["detail"][0]
    assert error["input"] == slug
    assert error["loc"] == ["path", "slug"]
    assert error["msg"] == f"Slug '{slug}' is not owned by the current user"
    assert error["type"] == "slug_not_owned_by_user"


def test_list_clicks__empty(client: TestClient, slug: str, target_url: str) -> None:
    client.post(
        url=f"{settings.API_VERSION_PREFIX}{settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    response = client.get(url=f"{settings.API_VERSION_PREFIX}{settings.LINKS_PREFIX}/{slug}/clicks")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data == []


def test_list_clicks__success(client: TestClient, slug: str, target_url: str) -> None:
    timestamp = datetime.now(tz=UTC)
    client.post(
        url=f"{settings.API_VERSION_PREFIX}{settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    response = client.get(url=f"{settings.API_VERSION_PREFIX}{settings.LINKS_PREFIX}/{slug}/clicks")
    data = response.json()
    assert len(data) == 0

    client.get(url=f"{settings.API_VERSION_PREFIX}{settings.FORWARD_PREFIX}/{slug}")
    client.get(
        url=f"{settings.API_VERSION_PREFIX}{settings.FORWARD_PREFIX}/{slug}",
        headers={
            "X-Client-IP": "192.168.1.1",
        },
    )

    response = client.get(url=f"{settings.API_VERSION_PREFIX}{settings.LINKS_PREFIX}/{slug}/clicks")
    data = response.json()

    timestamps = [item["timestamp"] for item in data]
    assert timestamps == sorted(timestamps, reverse=True)
    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 2
    for item in data:
        item_timestamp = datetime.fromisoformat(item["timestamp"]).replace(tzinfo=UTC)
        assert timestamp < item_timestamp < timestamp + timedelta(seconds=1)
        assert set(item.keys()) == {"ip_address", "timestamp"}
    assert {item["ip_address"] for item in data} == {"unknown", "192.168.1.1"}
