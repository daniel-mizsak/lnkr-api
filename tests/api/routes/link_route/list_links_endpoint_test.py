"""
Tests for the list links endpoint.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest import mock

from fastapi import status

from lnkr.api.routes import link_route
from lnkr.config.application_settings import application_settings
from lnkr.models import Link, LinkStatus

if TYPE_CHECKING:
    from httpx2 import AsyncClient

    from lnkr.models import User


async def test_list_links__empty_page(client: AsyncClient) -> None:
    response = await client.get(url=f"{application_settings.LINKS_PREFIX}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "items": [],
        "total": 0,
        "page": 1,
        "per_page": 10,
        "has_next": False,
    }


async def test_list_links__trimmed_search_and_single_item_page(
    client: AsyncClient,
    slug: str,
    target_url: str,
) -> None:
    await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    response = await client.get(
        url=f"{application_settings.LINKS_PREFIX}",
        params={"search": f" {slug} ", "per_page": 1, "page": 1},
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["total"] == 1
    assert data["page"] == 1
    assert data["per_page"] == 1
    assert data["has_next"] is False
    assert [item["slug"] for item in data["items"]] == [slug]
    assert [item["target_url"] for item in data["items"]] == [target_url]


async def test_list_links__query_parameters_and_next_page_metadata(
    client: AsyncClient,
    user: User,
    slug: str,
    target_url: str,
) -> None:
    timestamp = datetime.now(tz=UTC)
    link = Link(
        slug=slug,
        target_url=target_url,
        status=LinkStatus.ACTIVE,
        favorite=False,
        created_at=timestamp,
        updated_at=timestamp,
        user=user,
    )
    list_links = mock.AsyncMock(return_value=([link], 5))
    favorites_only = True
    with mock.patch.object(link_route, "list_links", list_links):
        response = await client.get(
            url=f"{application_settings.LINKS_PREFIX}",
            params={
                "search": "search",
                "favorites_only": favorites_only,
                "sort": "created_at",
                "direction": "ascending",
                "per_page": 2,
                "page": 2,
            },
        )

    data = response.json()
    assert response.status_code == status.HTTP_200_OK
    assert data["total"] == 5
    assert data["page"] == 2
    assert data["per_page"] == 2
    assert data["has_next"] is True
    assert [item["slug"] for item in data["items"]] == [slug]
    list_links.assert_awaited_once_with(
        mock.ANY,
        user,
        "search",
        favorites_only,
        "created_at",
        "ascending",
        2,
        2,
    )
