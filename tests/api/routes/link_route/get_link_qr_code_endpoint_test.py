"""
Tests for the get link qr code endpoint.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

import io
from typing import TYPE_CHECKING

import segno
from fastapi import status

from lnkr.config.application_settings import application_settings

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from lnkr.models import User
    from tests.api.conftest import OverrideGetCurrentUserFunction


def _expected_qr_code(slug: str) -> bytes:
    buffer = io.BytesIO()
    short_url = f"{application_settings.FRONTEND_FORWARD_URL}/{slug}"
    segno.make(short_url, error="M").save(buffer, kind="png", scale=20)
    return buffer.getvalue()


def test_get_link_qr_code__slug_does_not_exist(client: TestClient, slug: str) -> None:
    response = client.get(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}/{slug}/qr",
    )
    data = response.json()

    assert response.status_code == status.HTTP_404_NOT_FOUND
    error = data["detail"][0]
    assert error["input"] == slug
    assert error["loc"] == ["path", "slug"]
    assert error["msg"] == f"Slug '{slug}' does not exist"
    assert error["type"] == "slug_does_not_exist"


def test_get_link_qr_code__slug_not_owned_by_user(
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
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}/{slug}/qr",
    )
    data = response.json()

    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = data["detail"][0]
    assert error["input"] == slug
    assert error["loc"] == ["path", "slug"]
    assert error["msg"] == f"Slug '{slug}' is not owned by the current user"
    assert error["type"] == "slug_not_owned_by_user"


def test_get_link_qr_code__success(client: TestClient, slug: str, target_url: str) -> None:
    client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    response = client.get(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}/{slug}/qr",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["Content-Type"] == "image/png"
    assert response.headers["Cache-Control"] == "private, max-age=86400"
    assert response.headers["Content-Disposition"] == f'inline; filename="{slug}.png"'
    png_signature = b"\x89PNG\r\n\x1a\n"
    assert response.content.startswith(png_signature)
    assert response.content == _expected_qr_code(slug)
