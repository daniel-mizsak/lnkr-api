"""
Tests for the forward to target url endpoint.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING

import pytest
from fastapi import status

from lnkr.config.application_settings import application_settings

if TYPE_CHECKING:
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


def test_forward_to_target_url__success(client: TestClient, slug: str, target_url: str) -> None:
    client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    response = client.get(url=f"{application_settings.API_VERSION_PREFIX}{application_settings.FORWARD_PREFIX}/{slug}")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["target_url"] == target_url


def test_forward_to_target_url__ip_address(client: TestClient, slug: str, target_url: str) -> None:
    client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    client.get(url=f"{application_settings.API_VERSION_PREFIX}{application_settings.FORWARD_PREFIX}/{slug}")
    client.get(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.FORWARD_PREFIX}/{slug}",
        headers={"X-Client-IP": "192.168.1.1"},
    )
    client.get(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.FORWARD_PREFIX}/{slug}",
        headers={"X-Client-IP": "not-an-ip"},
    )

    response = client.get(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}/{slug}/clicks"
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 3
    assert [item["ip_address"] for item in data] == [None, "192.168.1.1", None]


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
