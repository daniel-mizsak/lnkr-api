"""
Tests for the generate random slug endpoint.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

import re
from typing import TYPE_CHECKING

from fastapi import status

from lnkr.config.application_settings import application_settings
from lnkr.database import link_database
from lnkr.services import link_service

if TYPE_CHECKING:
    import pytest
    from fastapi.testclient import TestClient
    from sqlalchemy.ext.asyncio import AsyncSession


def test_generate_random_slug__success(client: TestClient) -> None:
    response = client.get(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}/slugs/random"
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["Cache-Control"] == "no-store"
    assert set(data.keys()) == {"slug"}
    assert re.fullmatch(r"^[a-zA-Z0-9]{6}$", data["slug"])


def test_generate_random_slug__skips_existing_slug(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    target_url: str,
) -> None:
    existing_slug = "existing-slug"
    unused_slug = "unused-slug"
    generated_slugs = [existing_slug, unused_slug]

    response = client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        json={"slug": existing_slug, "target_url": target_url},
    )
    assert response.status_code == status.HTTP_201_CREATED

    # First call returns existing_slug, second call returns the unused_slug.
    def _generate_random_slug(_random_slug_length: int) -> str:
        return generated_slugs.pop(0)

    monkeypatch.setattr(link_service, "_generate_random_slug", _generate_random_slug)

    response = client.get(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}/slugs/random"
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["slug"] == unused_slug


def test_generate_random_slug__random_slug_generation_attempts_exhausted(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    # Not returning None for non-existing slugs will exhaust the random slug generation attempts.
    async def _get_link_by_slug(_session: AsyncSession, _slug: str) -> object:
        return object()

    monkeypatch.setattr(link_database, "get_link_by_slug", _get_link_by_slug)

    response = client.get(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}/slugs/random"
    )
    data = response.json()

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    error = data["detail"][0]
    assert error["msg"] == "Unable to generate an unused random slug. Please try again."
    assert error["type"] == "random_slug_generation_failed"
