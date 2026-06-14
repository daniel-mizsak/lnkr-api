"""
Tests for the generate random slug endpoint.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

import re
from typing import TYPE_CHECKING

from fastapi import status

from lnkr.config.application_settings import application_settings
from lnkr.services import link_service

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def test_generate_random_slug__success(client: TestClient) -> None:
    response = client.get(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}/slugs/random"
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["Cache-Control"] == "no-store"
    assert set(data.keys()) == {"slug"}
    assert re.fullmatch(r"^[a-zA-Z0-9]{6}$", data["slug"])


def test_generate_random_slug__skips_existing_slug(client: TestClient, monkeypatch, target_url: str) -> None:
    existing_slug = "aaaaaa"
    unused_slug = "bbbbbbb"

    client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        json={"slug": existing_slug, "target_url": target_url},
    )

    def _generate_random_slug(random_slug_length: int) -> str:
        if random_slug_length == 6:
            return existing_slug
        return unused_slug

    monkeypatch.setattr(link_service, "_generate_random_slug", _generate_random_slug)

    response = client.get(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}/slugs/random"
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["slug"] == unused_slug
