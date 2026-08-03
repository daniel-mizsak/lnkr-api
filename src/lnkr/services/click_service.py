"""
High level services for click management.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

from datetime import UTC, datetime, timedelta
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
    """List a cursor-paginated collection of clicks for a given link."""
    limit = min(limit, 100)
    clicks = await click_database.list_clicks_by_link(session, link, limit=limit + 1, cursor=cursor)

    has_next = len(clicks) > limit
    clicks = clicks[:limit]
    next_cursor = ClickCursor.from_click(clicks[-1]).encode() if has_next else None
    return clicks, next_cursor


async def list_click_counts(session: AsyncSession, links: Sequence[Link]) -> dict[uuid.UUID, int]:
    """List total click counts for links."""
    if not links:
        return {}

    total_click_counts_by_link_id = await click_database.count_clicks_by_links(session, links)
    return {link.id: total_click_counts_by_link_id.get(link.id, 0) for link in links}


async def get_click_analytics(session: AsyncSession, link: Link, timezone: ZoneInfo) -> ClickAnalyticsRead:
    """Get click analytics dashboard data."""
    now = datetime.now(tz=UTC)
    period_days = 4 * 7
    today = now.astimezone(timezone).date()
    period = ClickAnalyticsPeriodRead(
        from_date=today - timedelta(days=period_days - 1),
        through_date=today,
        timezone=timezone.key,
    )

    return ClickAnalyticsRead(
        summary=await get_click_analytics_summary(session, link, now),
        daily_clicks=await get_click_analytics_daily_clicks(session, link, period),
        top_countries=await get_click_analytics_top_countries(session, link, period),
    )


async def get_click_analytics_summary(session: AsyncSession, link: Link, now: datetime) -> ClickAnalyticsSummaryRead:
    """Get summary click analytics for a link."""
    total_period = ClickAnalyticsTimeRange(start=link.created_at, end=now)
    last_7_days_period = ClickAnalyticsTimeRange(start=now - timedelta(days=7), end=now)
    summary_periods = (total_period, last_7_days_period)
    total_clicks, last_7_days_clicks = await click_database.count_clicks_by_periods(session, link, summary_periods)
    return ClickAnalyticsSummaryRead(total_clicks=total_clicks, last_7_days_clicks=last_7_days_clicks)


async def get_click_analytics_daily_clicks(
    session: AsyncSession,
    link: Link,
    period: ClickAnalyticsPeriodRead,
) -> ClickAnalyticsDailyClicksRead:
    """Get daily click analytics for a link."""
    daily_counts = await click_database.list_daily_click_counts(session, link, period.to_time_range(), period.timezone)
    period_days = (period.through_date - period.from_date).days + 1
    days = [
        ClickAnalyticsDailyCountRead(
            date=period.from_date + timedelta(days=day_offset),
            clicks=daily_counts.get(period.from_date + timedelta(days=day_offset), 0),
        )
        for day_offset in range(period_days)
    ]
    return ClickAnalyticsDailyClicksRead(period=period, days=days)


async def get_click_analytics_top_countries(
    session: AsyncSession,
    link: Link,
    period: ClickAnalyticsPeriodRead,
) -> ClickAnalyticsTopCountriesRead:
    """Get the top countries with the most clicks for a link."""
    known_country_click_count, top_country_counts = await click_database.list_top_country_click_counts(
        session,
        link,
        period.to_time_range(),
        limit=5,
    )
    countries: list[ClickAnalyticsCountryCountRead] = []
    if known_country_click_count != 0:
        for country_code, clicks in top_country_counts:
            percentage = round(clicks / known_country_click_count * 100, 2)
            countries.append(
                ClickAnalyticsCountryCountRead(
                    country_code=country_code,
                    clicks=clicks,
                    percentage=percentage,
                )
            )
    return ClickAnalyticsTopCountriesRead(
        period=period,
        known_country_click_count=known_country_click_count,
        countries=countries,
    )
