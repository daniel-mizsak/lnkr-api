"""
Low level database operations for click management.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING

from sqlalchemy import Date, cast, func, select, tuple_

from lnkr.models import Click, ClickAnalyticsTimeRange, ClickCursor, ClickSource, Link

if TYPE_CHECKING:
    import uuid
    from collections.abc import Collection, Sequence
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
    sources: Collection[ClickSource] | None = None,
) -> list[Click]:
    """List clicks for a link."""
    filters = [Click.link_id == link.id]
    if sources is not None:
        if not sources:
            return []
        filters.append(Click.source.in_(tuple(sources)))
    if cursor is not None:
        filters.append(tuple_(Click.timestamp, Click.id) < (cursor.timestamp, cursor.id))

    statement = select(Click).where(*filters).order_by(Click.timestamp.desc(), Click.id.desc()).limit(limit)
    result = await session.execute(statement)
    return list(result.scalars().all())


async def count_clicks_by_links(session: AsyncSession, links: Sequence[Link]) -> dict[uuid.UUID, int]:
    """Count clicks for each link."""
    if not links:
        return {}

    click_count = func.count().label("click_count")
    filters = [Click.link_id.in_([link.id for link in links]), Click.source == ClickSource.LNKR_APP]

    statement = select(Click.link_id, click_count).where(*filters).group_by(Click.link_id)
    result = await session.execute(statement)
    return {row.link_id: int(row.click_count) for row in result.all()}


async def count_clicks_by_periods(
    session: AsyncSession,
    link: Link,
    periods: Sequence[ClickAnalyticsTimeRange],
) -> list[int]:
    """Count clicks for each period."""
    if not periods:
        return []

    count_expressions = [
        func.count().filter(Click.timestamp >= period.start, Click.timestamp < period.end).label(f"period_{index}")
        for index, period in enumerate(periods)
    ]
    filters = [Click.link_id == link.id, Click.source == ClickSource.LNKR_APP]

    statement = select(*count_expressions).where(*filters)
    result = await session.execute(statement)
    return [int(count) for count in result.one()]


async def list_daily_click_counts(
    session: AsyncSession,
    link: Link,
    period: ClickAnalyticsTimeRange,
    timezone: str,
) -> dict[date, int]:
    """List timezone-local daily click counts."""
    click_date = cast(func.timezone(timezone, Click.timestamp), Date).label("click_date")
    filters = [
        Click.link_id == link.id,
        Click.source == ClickSource.LNKR_APP,
        Click.timestamp >= period.start,
        Click.timestamp < period.end,
    ]

    statement = (
        select(click_date, func.count().label("click_count")).where(*filters).group_by(click_date).order_by(click_date)
    )
    result = await session.execute(statement)
    return {row.click_date: row.click_count for row in result.all()}


async def list_top_country_click_counts(
    session: AsyncSession,
    link: Link,
    period: ClickAnalyticsTimeRange,
    limit: int,
) -> tuple[int, list[tuple[str, int]]]:
    """List country click counts and the known-country total."""
    click_count = func.count().label("click_count")
    known_country_click_count = func.sum(func.count()).over().label("known_country_click_count")
    filters = [
        Click.link_id == link.id,
        Click.source == ClickSource.LNKR_APP,
        Click.timestamp >= period.start,
        Click.timestamp < period.end,
        Click.country_code.is_not(None),
    ]

    statement = (
        select(Click.country_code, click_count, known_country_click_count)
        .where(*filters)
        .group_by(Click.country_code)
        .order_by(click_count.desc(), Click.country_code.asc())
        .limit(limit)
    )
    result = await session.execute(statement)
    rows = result.all()
    if not rows:
        return 0, []
    return int(rows[0].known_country_click_count), [(row.country_code, int(row.click_count)) for row in rows]
