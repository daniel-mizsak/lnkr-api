"""
Tests for the click service.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

import uuid
from datetime import UTC, date, datetime, timedelta
from unittest import mock
from zoneinfo import ZoneInfo

from lnkr.models import (
    Click,
    ClickAnalyticsCountryCountRead,
    ClickAnalyticsDailyClicksRead,
    ClickAnalyticsDailyCountRead,
    ClickAnalyticsPeriodRead,
    ClickAnalyticsSummaryRead,
    ClickAnalyticsTimeRange,
    ClickAnalyticsTopCountriesRead,
    ClickCursor,
    ClickSource,
    Link,
)
from lnkr.services import click_service


async def test_list_clicks__caps_limit_and_encodes_next_cursor(link: Link) -> None:
    session = mock.AsyncMock()
    timestamp = datetime.now(tz=UTC)
    database_clicks = [
        Click(
            id=uuid.UUID(int=index + 1),
            timestamp=timestamp,
            source=ClickSource.LNKR_APP,
            link_id=link.id,
        )
        for index in range(101)
    ]
    list_clicks_by_link = mock.AsyncMock(return_value=database_clicks)
    with mock.patch.object(click_service.click_database, "list_clicks_by_link", list_clicks_by_link):
        clicks, next_cursor = await click_service.list_clicks(session, link, 500, None)

    assert clicks == database_clicks[:100]
    assert next_cursor == ClickCursor.from_click(database_clicks[99]).encode()
    list_clicks_by_link.assert_awaited_once_with(session, link, limit=101, cursor=None)


async def test_list_clicks__last_page_has_no_cursor(link: Link) -> None:
    session = mock.AsyncMock()
    click = Click(source=ClickSource.LNKR_APP, link_id=link.id)
    list_clicks_by_link = mock.AsyncMock(return_value=[click])
    with mock.patch.object(click_service.click_database, "list_clicks_by_link", list_clicks_by_link):
        clicks, next_cursor = await click_service.list_clicks(session, link, 10, None)

    assert clicks == [click]
    assert next_cursor is None
    list_clicks_by_link.assert_awaited_once_with(session, link, limit=11, cursor=None)


async def test_list_click_counts__empty_collection_avoids_database() -> None:
    session = mock.AsyncMock()
    count_clicks_by_links = mock.AsyncMock()
    with mock.patch.object(click_service.click_database, "count_clicks_by_links", count_clicks_by_links):
        click_counts = await click_service.list_click_counts(session, [])

    assert click_counts == {}
    count_clicks_by_links.assert_not_awaited()


async def test_list_click_counts__fills_missing_links_with_zero(link: Link, link_other: Link) -> None:
    session = mock.AsyncMock()
    count_clicks_by_links = mock.AsyncMock(return_value={link.id: 3})
    with mock.patch.object(click_service.click_database, "count_clicks_by_links", count_clicks_by_links):
        click_counts = await click_service.list_click_counts(session, [link, link_other])

    assert click_counts == {link.id: 3, link_other.id: 0}
    count_clicks_by_links.assert_awaited_once_with(session, [link, link_other])


async def test_get_click_analytics__uses_four_week_local_date_period(link: Link) -> None:
    session = mock.AsyncMock()
    timezone = ZoneInfo("Europe/Copenhagen")
    now = datetime(2026, 1, 27, 23, 30, tzinfo=UTC)
    period = ClickAnalyticsPeriodRead(
        from_date=date(2026, 1, 1),
        through_date=date(2026, 1, 28),
        timezone=timezone.key,
    )
    summary = ClickAnalyticsSummaryRead(total_clicks=12, last_7_days_clicks=4)
    daily_clicks = ClickAnalyticsDailyClicksRead(period=period, days=[])
    top_countries = ClickAnalyticsTopCountriesRead(
        period=period,
        known_country_click_count=0,
        countries=[],
    )
    get_summary = mock.AsyncMock(return_value=summary)
    get_daily_clicks = mock.AsyncMock(return_value=daily_clicks)
    get_top_countries = mock.AsyncMock(return_value=top_countries)
    # datetime.now cannot be patched directly, so replace the imported class while wrapping its real behavior.
    datetime_mock = mock.Mock(wraps=datetime)
    datetime_mock.now.return_value = now
    with (
        mock.patch.object(click_service, "datetime", datetime_mock),
        mock.patch.object(click_service, "get_click_analytics_summary", get_summary),
        mock.patch.object(click_service, "get_click_analytics_daily_clicks", get_daily_clicks),
        mock.patch.object(click_service, "get_click_analytics_top_countries", get_top_countries),
    ):
        analytics = await click_service.get_click_analytics(session, link, timezone)

    assert analytics.summary == summary
    assert analytics.daily_clicks == daily_clicks
    assert analytics.top_countries == top_countries
    get_summary.assert_awaited_once_with(session, link, now)
    get_daily_clicks.assert_awaited_once_with(session, link, period)
    get_top_countries.assert_awaited_once_with(session, link, period)


async def test_get_click_analytics_summary__counts_total_and_last_seven_days(link: Link) -> None:
    session = mock.AsyncMock()
    now = datetime(2026, 1, 1, 12, tzinfo=UTC)
    link.created_at = now - timedelta(days=30)
    count_clicks_by_periods = mock.AsyncMock(return_value=[12, 4])
    with mock.patch.object(click_service.click_database, "count_clicks_by_periods", count_clicks_by_periods):
        summary = await click_service.get_click_analytics_summary(session, link, now)

    assert summary == ClickAnalyticsSummaryRead(total_clicks=12, last_7_days_clicks=4)
    count_clicks_by_periods.assert_awaited_once_with(
        session,
        link,
        (
            ClickAnalyticsTimeRange(start=link.created_at, end=now),
            ClickAnalyticsTimeRange(start=now - timedelta(days=7), end=now),
        ),
    )


async def test_get_click_analytics_daily_clicks__fills_days_without_clicks_across_daylight_saving_time_transition(
    link: Link,
) -> None:
    session = mock.AsyncMock()
    period = ClickAnalyticsPeriodRead(
        from_date=date(2026, 3, 28),
        through_date=date(2026, 3, 30),
        timezone="Europe/Copenhagen",
    )
    list_daily_click_counts = mock.AsyncMock(
        return_value={
            date(2026, 3, 28): 2,
            date(2026, 3, 30): 1,
        }
    )
    with mock.patch.object(click_service.click_database, "list_daily_click_counts", list_daily_click_counts):
        daily_clicks = await click_service.get_click_analytics_daily_clicks(session, link, period)

    assert daily_clicks.period == period
    assert daily_clicks.days == [
        ClickAnalyticsDailyCountRead(date=date(2026, 3, 28), clicks=2),
        ClickAnalyticsDailyCountRead(date=date(2026, 3, 29), clicks=0),
        ClickAnalyticsDailyCountRead(date=date(2026, 3, 30), clicks=1),
    ]
    list_daily_click_counts.assert_awaited_once_with(
        session,
        link,
        ClickAnalyticsTimeRange(
            start=datetime(2026, 3, 27, 23, tzinfo=UTC),
            end=datetime(2026, 3, 30, 22, tzinfo=UTC),
        ),
        period.timezone,
    )


async def test_get_click_analytics_top_countries__calculates_known_country_percentages(link: Link) -> None:
    session = mock.AsyncMock()
    period = ClickAnalyticsPeriodRead(
        from_date=date(2026, 1, 1),
        through_date=date(2026, 1, 28),
        timezone="UTC",
    )
    list_top_country_click_counts = mock.AsyncMock(return_value=(8, [("US", 5), ("DK", 3)]))
    with mock.patch.object(
        click_service.click_database, "list_top_country_click_counts", list_top_country_click_counts
    ):
        top_countries = await click_service.get_click_analytics_top_countries(session, link, period)

    assert top_countries.period == period
    assert top_countries.known_country_click_count == 8
    assert top_countries.countries == [
        ClickAnalyticsCountryCountRead(country_code="US", clicks=5, percentage=62.5),
        ClickAnalyticsCountryCountRead(country_code="DK", clicks=3, percentage=37.5),
    ]
    list_top_country_click_counts.assert_awaited_once_with(session, link, period.to_time_range(), limit=5)


async def test_get_click_analytics_top_countries__handles_no_known_countries(link: Link) -> None:
    session = mock.AsyncMock()
    period = ClickAnalyticsPeriodRead(
        from_date=date(2026, 1, 1),
        through_date=date(2026, 1, 28),
        timezone="UTC",
    )
    list_top_country_click_counts = mock.AsyncMock(return_value=(0, []))
    with mock.patch.object(
        click_service.click_database, "list_top_country_click_counts", list_top_country_click_counts
    ):
        top_countries = await click_service.get_click_analytics_top_countries(session, link, period)

    assert top_countries.known_country_click_count == 0
    assert top_countries.countries == []
    list_top_country_click_counts.assert_awaited_once_with(session, link, period.to_time_range(), limit=5)
