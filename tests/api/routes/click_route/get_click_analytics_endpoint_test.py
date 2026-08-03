"""
Tests for the get click analytics endpoint.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

from datetime import date
from typing import TYPE_CHECKING
from unittest import mock
from zoneinfo import ZoneInfo

from fastapi import status

from lnkr.api.routes import click_route
from lnkr.config.application_settings import application_settings
from lnkr.exceptions import SlugNotOwnedByUserError
from lnkr.models import (
    ClickAnalyticsCountryCountRead,
    ClickAnalyticsDailyClicksRead,
    ClickAnalyticsDailyCountRead,
    ClickAnalyticsPeriodRead,
    ClickAnalyticsRead,
    ClickAnalyticsSummaryRead,
    ClickAnalyticsTopCountriesRead,
)

if TYPE_CHECKING:
    from httpx2 import AsyncClient


async def test_get_click_analytics__slug_does_not_exist(client: AsyncClient, slug: str) -> None:
    response = await client.get(url=f"{application_settings.LINKS_PREFIX}/{slug}/analytics")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"][0]["type"] == "slug_does_not_exist"


async def test_get_click_analytics__slug_not_owned_by_user(client: AsyncClient, slug: str) -> None:
    with mock.patch.object(
        click_route,
        "get_link_validate_user",
        mock.AsyncMock(side_effect=SlugNotOwnedByUserError(slug)),
    ):
        response = await client.get(url=f"{application_settings.LINKS_PREFIX}/{slug}/analytics")

    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = response.json()["detail"][0]
    assert error["input"] == slug
    assert error["loc"] == ["path", "slug"]
    assert error["type"] == "slug_not_owned_by_user"


async def test_get_click_analytics__invalid_timezone(client: AsyncClient, slug: str, target_url: str) -> None:
    timezone = "Not/A-Timezone"
    await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    response = await client.get(
        url=f"{application_settings.LINKS_PREFIX}/{slug}/analytics",
        params={"timezone": timezone},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    error = response.json()["detail"][0]
    assert error["input"] == timezone
    assert error["loc"] == ["query", "timezone"]
    assert error["type"] == "timezone_invalid"


async def test_get_click_analytics__response_and_timezone(client: AsyncClient, slug: str, target_url: str) -> None:
    await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    period = ClickAnalyticsPeriodRead(
        from_date=date(2026, 1, 1),
        through_date=date(2026, 1, 28),
        timezone="Europe/Copenhagen",
    )
    analytics = ClickAnalyticsRead(
        summary=ClickAnalyticsSummaryRead(total_clicks=10, last_7_days_clicks=4),
        daily_clicks=ClickAnalyticsDailyClicksRead(
            period=period,
            days=[ClickAnalyticsDailyCountRead(date=date(2026, 1, 1), clicks=2)],
        ),
        top_countries=ClickAnalyticsTopCountriesRead(
            period=period,
            known_country_click_count=3,
            countries=[
                ClickAnalyticsCountryCountRead(
                    country_code="DK",
                    clicks=2,
                    percentage=66.67,
                )
            ],
        ),
    )
    get_click_analytics = mock.AsyncMock(return_value=analytics)
    with mock.patch.object(click_route, "get_click_analytics", get_click_analytics):
        response = await client.get(
            url=f"{application_settings.LINKS_PREFIX}/{slug}/analytics",
            params={"timezone": period.timezone},
        )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "summary": {
            "total_clicks": 10,
            "last_7_days_clicks": 4,
        },
        "daily_clicks": {
            "period": {
                "from_date": "2026-01-01",
                "through_date": "2026-01-28",
                "timezone": "Europe/Copenhagen",
            },
            "days": [{"date": "2026-01-01", "clicks": 2}],
        },
        "top_countries": {
            "period": {
                "from_date": "2026-01-01",
                "through_date": "2026-01-28",
                "timezone": "Europe/Copenhagen",
            },
            "known_country_click_count": 3,
            "countries": [
                {
                    "country_code": "DK",
                    "clicks": 2,
                    "percentage": 66.67,
                }
            ],
        },
    }
    get_click_analytics.assert_awaited_once()
    await_args = get_click_analytics.await_args
    assert await_args is not None
    _, requested_link, requested_timezone = await_args.args
    assert requested_link.slug == slug
    assert requested_timezone == ZoneInfo(period.timezone)
