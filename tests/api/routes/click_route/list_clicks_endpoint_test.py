"""
Tests for the list clicks endpoint.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest import mock

from fastapi import status

from lnkr.api.dependencies.header import CLIENT_IP_HEADER, FRONTEND_API_KEY_HEADER, USER_AGENT_HEADER
from lnkr.api.routes import click_route
from lnkr.config.application_settings import application_settings
from lnkr.exceptions import SlugNotOwnedByUserError
from lnkr.models.click_model import CLICK_CURSOR_MAX_LENGTH

if TYPE_CHECKING:
    from httpx2 import AsyncClient


async def test_list_clicks__slug_does_not_exist(client: AsyncClient, slug: str) -> None:
    response = await client.get(url=f"{application_settings.LINKS_PREFIX}/{slug}/clicks")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"][0]["type"] == "slug_does_not_exist"


async def test_list_clicks__slug_not_owned_by_user(client: AsyncClient, slug: str) -> None:
    with mock.patch.object(
        click_route,
        "get_link_validate_user",
        mock.AsyncMock(side_effect=SlugNotOwnedByUserError(slug)),
    ):
        response = await client.get(url=f"{application_settings.LINKS_PREFIX}/{slug}/clicks")

    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = response.json()["detail"][0]
    assert error["input"] == slug
    assert error["loc"] == ["path", "slug"]
    assert error["type"] == "slug_not_owned_by_user"


async def test_list_clicks__invalid_cursor(client: AsyncClient, slug: str, target_url: str) -> None:
    await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    response = await client.get(
        url=f"{application_settings.LINKS_PREFIX}/{slug}/clicks",
        params={"cursor": "invalid"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"][0]["type"] == "cursor_invalid"


async def test_list_clicks__cursor_too_long(client: AsyncClient, slug: str, target_url: str) -> None:
    await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    response = await client.get(
        url=f"{application_settings.LINKS_PREFIX}/{slug}/clicks",
        params={"cursor": "a" * (CLICK_CURSOR_MAX_LENGTH + 1)},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    error = response.json()["detail"][0]
    assert error["loc"] == ["query", "cursor"]
    assert error["type"] == "string_too_long"


async def test_list_clicks__recorded_click_metadata(
    client: AsyncClient,
    slug: str,
    target_url: str,
    frontend_api_key: str,
    ip_address_public: str,
    ip_address_public_country_code: str,
    user_agent: str,
) -> None:
    before = datetime.now(tz=UTC)
    await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )
    await client.get(
        url=f"{application_settings.FORWARD_PREFIX}/{slug}",
        headers={
            FRONTEND_API_KEY_HEADER: frontend_api_key,
            CLIENT_IP_HEADER: ip_address_public,
            USER_AGENT_HEADER: user_agent,
        },
    )

    response = await client.get(url=f"{application_settings.LINKS_PREFIX}/{slug}/clicks")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["next_cursor"] is None
    assert len(data["items"]) == 1
    click = data["items"][0]
    assert set(click) == {"timestamp", "ip_address", "country_code", "browser", "operating_system"}
    assert before <= datetime.fromisoformat(click["timestamp"]) <= before + timedelta(seconds=1)
    assert click["ip_address"] == ip_address_public
    assert click["country_code"] == ip_address_public_country_code
    assert click["browser"] == "Chrome"
    assert click["operating_system"] == "Mac OS X"
