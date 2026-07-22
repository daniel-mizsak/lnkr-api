"""
Tests for the generate random slug endpoint.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

import re
from typing import TYPE_CHECKING
from unittest import mock

from fastapi import status

from lnkr.api.routes import link_route
from lnkr.config.application_settings import application_settings
from lnkr.exceptions import RandomSlugGenerationError

if TYPE_CHECKING:
    from httpx2 import AsyncClient


async def test_generate_random_slug__generation_failure(client: AsyncClient) -> None:
    with mock.patch.object(
        link_route,
        "generate_unused_random_slug",
        mock.AsyncMock(side_effect=RandomSlugGenerationError()),
    ):
        response = await client.get(url=f"{application_settings.LINKS_PREFIX}/slugs/random")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.headers["Cache-Control"] == "no-store"
    error = response.json()["detail"][0]
    assert error["msg"] == "Unable to generate an unused random slug. Please try again."
    assert error["type"] == "random_slug_generation_failed"


async def test_generate_random_slug__slug_format_and_cache_policy(client: AsyncClient) -> None:
    response = await client.get(url=f"{application_settings.LINKS_PREFIX}/slugs/random")

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["Cache-Control"] == "no-store"
    assert re.fullmatch(r"^[a-zA-Z0-9]{6}$", response.json()["slug"])
