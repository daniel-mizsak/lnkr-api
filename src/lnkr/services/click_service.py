"""
High level services for click management.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from datetime import UTC, datetime, time, timedelta
from typing import TYPE_CHECKING

from sqlalchemy.exc import SQLAlchemyError

from lnkr.database import click_database
from lnkr.models import (
    Click,
    ClickAnalyticsCountryCountRead,
    ClickAnalyticsDailyClicksRead,
    ClickAnalyticsDailyCountRead,
    ClickAnalyticsPeriodRead,
    ClickAnalyticsRead,
    ClickAnalyticsRecentClickRead,
    ClickAnalyticsSummaryRead,
    ClickAnalyticsTimeRange,
    ClickAnalyticsTopCountriesRead,
    ClickCreate,
    ClickCursor,
    Link,
)
from lnkr.services.geoip_service import get_country_code_from_ip

if TYPE_CHECKING:
    import uuid
    from collections.abc import Sequence
    from zoneinfo import ZoneInfo

    from geoip2.database import Reader
    from sqlalchemy.ext.asyncio import AsyncSession


async def create_click(
    session: AsyncSession,
    geoip_reader: Reader,
    click_create: ClickCreate,
    link_id: uuid.UUID,
) -> Click:
    """Create a click in the database."""
    country_code = get_country_code_from_ip(geoip_reader, click_create.ip_address)
    click = Click.from_click_create(click_create, country_code, link_id)

    try:
        await click_database.save_click(session, click)
        await session.commit()
        await session.refresh(click)
    except SQLAlchemyError:
        await session.rollback()
        raise

    return click


async def list_clicks(
    session: AsyncSession,
    link: Link,
    limit: int,
    cursor: ClickCursor | None,
) -> tuple[list[Click], str | None]:
    """List a cursor-paginated collection of trusted clicks for a given link."""
    limit = min(limit, 100)
    clicks, has_next = await click_database.list_clicks_by_link(session, link, limit, cursor)

    next_cursor = ClickCursor.from_click(clicks[-1]).encode() if has_next else None
    return clicks, next_cursor


async def list_trusted_click_counts(session: AsyncSession, links: Sequence[Link]) -> dict[uuid.UUID, int]:
    """List total trusted click counts for links."""
    if not links:
        return {}

    total_click_counts_by_link_id = await click_database.count_total_trusted_clicks_by_links(session, links)
    return {link.id: total_click_counts_by_link_id.get(link.id, 0) for link in links}


async def get_click_analytics(session: AsyncSession, link: Link, timezone: ZoneInfo) -> ClickAnalyticsRead:
    """Get click analytics dashboard data."""
    now = datetime.now(tz=UTC)
    period_days = 4 * 7
    local_now = now.astimezone(timezone)
    today_start = datetime.combine(local_now.date(), time.min, tzinfo=timezone)
    from_date = today_start.date() - timedelta(days=period_days - 1)
    period = ClickAnalyticsTimeRange(
        start=datetime.combine(from_date, time.min, tzinfo=timezone).astimezone(UTC),
        end=(today_start + timedelta(days=1)).astimezone(UTC),
    )
    analytics_period = ClickAnalyticsPeriodRead(
        from_date=from_date,
        through_date=today_start.date(),
        timezone=timezone.key,
    )

    return ClickAnalyticsRead(
        summary=await get_click_analytics_summary(session, link, now),
        daily_clicks=await get_click_analytics_daily_clicks(session, link, period, analytics_period),
        recent_clicks=await get_click_analytics_recent_clicks(session, link),
        top_countries=await get_click_analytics_top_countries(session, link, period, analytics_period),
    )


async def get_click_analytics_summary(session: AsyncSession, link: Link, now: datetime) -> ClickAnalyticsSummaryRead:
    """Get summary click analytics for a link."""
    total_period = ClickAnalyticsTimeRange(start=link.created_at, end=now)
    last_7_days_period = ClickAnalyticsTimeRange(start=now - timedelta(days=7), end=now)
    summary_periods = (total_period, last_7_days_period)
    total_clicks, last_7_days_clicks = await click_database.count_trusted_clicks_by_periods(
        session,
        link,
        summary_periods,
    )
    return ClickAnalyticsSummaryRead(
        total_clicks=total_clicks,
        last_7_days_clicks=last_7_days_clicks,
    )


async def get_click_analytics_daily_clicks(
    session: AsyncSession,
    link: Link,
    period: ClickAnalyticsTimeRange,
    analytics_period: ClickAnalyticsPeriodRead,
) -> ClickAnalyticsDailyClicksRead:
    """Get daily click analytics for a link."""
    daily_counts = await click_database.list_daily_click_counts(session, link, period, analytics_period.timezone)
    period_days = (analytics_period.through_date - analytics_period.from_date).days + 1
    days = [
        ClickAnalyticsDailyCountRead(
            date=analytics_period.from_date + timedelta(days=day_offset),
            clicks=daily_counts.get(analytics_period.from_date + timedelta(days=day_offset), 0),
        )
        for day_offset in range(period_days)
    ]
    return ClickAnalyticsDailyClicksRead(period=analytics_period, days=days)


async def get_click_analytics_recent_clicks(
    session: AsyncSession,
    link: Link,
) -> list[ClickAnalyticsRecentClickRead]:
    """Get the ten most recent trusted clicks for a link."""
    recent_clicks = await click_database.list_trusted_clicks_by_link(session, link, per_page=10, page=1)
    return [
        ClickAnalyticsRecentClickRead(timestamp=click.timestamp, country_code=click.country_code)
        for click in recent_clicks
    ]


async def get_click_analytics_top_countries(
    session: AsyncSession,
    link: Link,
    period: ClickAnalyticsTimeRange,
    analytics_period: ClickAnalyticsPeriodRead,
) -> ClickAnalyticsTopCountriesRead:
    """Get the five countries with the most trusted clicks for a link."""
    located_click_count, top_country_counts = await click_database.list_top_country_click_counts(
        session,
        link,
        period,
        limit=5,
    )
    countries = [
        ClickAnalyticsCountryCountRead(
            country_code=country_code,
            clicks=clicks,
            percentage=round(clicks / located_click_count * 100, 2),
        )
        for country_code, clicks in top_country_counts
        if located_click_count != 0
    ]
    return ClickAnalyticsTopCountriesRead(
        period=analytics_period,
        located_click_count=located_click_count,
        countries=countries,
    )
