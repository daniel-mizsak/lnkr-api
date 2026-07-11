"""
Low level database operations for click management.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING

from sqlalchemy import Date, and_, cast, func, or_, select

from lnkr.models import Click, ClickAnalyticsTimeRange, ClickCursor, ClickSource, Link

if TYPE_CHECKING:
    import uuid
    from collections.abc import Sequence
    from datetime import date

    from sqlalchemy.ext.asyncio import AsyncSession


async def save_click(session: AsyncSession, click: Click) -> Click:
    """Persist a click without committing the transaction."""
    session.add(click)
    await session.flush()
    return click


async def list_clicks_by_link(
    session: AsyncSession,
    link: Link,
    limit: int,
    cursor: ClickCursor | None,
) -> tuple[list[Click], bool]:
    """List a page of clicks for a link and whether another page exists.

    Only trusted clicks are returned, where the source is the lnkr application.
    """
    statement = select(Click).where(Click.link_id == link.id, Click.source == ClickSource.LNKR_APP)
    if cursor is not None:
        statement = statement.where(
            or_(
                Click.timestamp < cursor.timestamp,
                and_(Click.timestamp == cursor.timestamp, Click.id < cursor.id),
            )
        )

    statement = statement.order_by(Click.timestamp.desc(), Click.id.desc()).limit(limit + 1)
    result = await session.execute(statement)
    clicks = list(result.scalars().all())
    has_next = len(clicks) > limit
    return clicks[:limit], has_next


async def list_trusted_clicks_by_link(session: AsyncSession, link: Link, per_page: int, page: int) -> list[Click]:
    """List trusted clicks for a link."""
    offset = (page - 1) * per_page
    statement = (
        select(Click)
        .where(Click.link_id == link.id, Click.source == ClickSource.LNKR_APP)
        .order_by(Click.timestamp.desc(), Click.id.desc())
        .offset(offset)
        .limit(per_page)
    )
    result = await session.execute(statement)
    return list(result.scalars().all())


async def count_total_trusted_clicks_by_links(session: AsyncSession, links: Sequence[Link]) -> dict[uuid.UUID, int]:
    """Count all trusted clicks for each link."""
    if not links:
        return {}

    click_count = func.count().label("click_count")
    statement = (
        select(Click.link_id, click_count)
        .where(
            Click.link_id.in_([link.id for link in links]),
            Click.source == ClickSource.LNKR_APP,
        )
        .group_by(Click.link_id)
    )
    result = await session.execute(statement)
    return {row.link_id: int(row.click_count) for row in result.all()}


async def count_trusted_clicks_by_periods(
    session: AsyncSession,
    link: Link,
    periods: Sequence[ClickAnalyticsTimeRange],
) -> list[int]:
    """Count trusted clicks for each period, preserving input order.

    The periods are half-open intervals, meaning that the start is inclusive and the end is exclusive.
    """
    if not periods:
        return []

    count_expressions = [
        func.count().filter(Click.timestamp >= period.start, Click.timestamp < period.end).label(f"period_{index}")
        for index, period in enumerate(periods)
    ]
    statement = select(*count_expressions).where(Click.link_id == link.id, Click.source == ClickSource.LNKR_APP)
    result = await session.execute(statement)
    return [int(count) for count in result.one()]


async def list_daily_click_counts(
    session: AsyncSession,
    link: Link,
    period: ClickAnalyticsTimeRange,
    timezone: str,
) -> dict[date, int]:
    """List timezone-local daily trusted click counts for a link within a period."""
    click_date = cast(func.timezone(timezone, Click.timestamp), Date).label("click_date")
    statement = (
        select(click_date, func.count().label("click_count"))
        .where(
            Click.link_id == link.id,
            Click.source == ClickSource.LNKR_APP,
            Click.timestamp >= period.start,
            Click.timestamp < period.end,
        )
        .group_by(click_date)
        .order_by(click_date)
    )
    result = await session.execute(statement)
    return {row.click_date: row.click_count for row in result.all()}


async def list_top_country_click_counts(
    session: AsyncSession,
    link: Link,
    period: ClickAnalyticsTimeRange,
    limit: int,
) -> tuple[int, list[tuple[str, int]]]:
    """List country counts and total located trusted clicks for a link within a period."""
    click_count = func.count().label("click_count")
    located_click_count = func.sum(func.count()).over().label("located_click_count")
    statement = (
        select(Click.country_code, click_count, located_click_count)
        .where(
            Click.link_id == link.id,
            Click.source == ClickSource.LNKR_APP,
            Click.timestamp >= period.start,
            Click.timestamp < period.end,
            Click.country_code.is_not(None),
        )
        .group_by(Click.country_code)
        .order_by(click_count.desc(), Click.country_code.asc())
        .limit(limit)
    )
    result = await session.execute(statement)
    rows = result.all()
    if not rows:
        return 0, []
    return int(rows[0].located_click_count), [(row.country_code, int(row.click_count)) for row in rows]
