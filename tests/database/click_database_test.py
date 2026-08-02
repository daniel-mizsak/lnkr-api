"""
Tests for click database operations.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

import uuid
from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING

from lnkr.database import click_database
from lnkr.models import Click, ClickAnalyticsTimeRange, ClickCursor, ClickSource, Link

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def test_list_clicks_by_link__cursor_pagination_uses_id_to_break_timestamp_ties(
    session: AsyncSession,
    link: Link,
) -> None:
    session.add(link)
    await session.flush()

    timestamp = datetime.now(tz=UTC)
    click_ids = [uuid.UUID(int=value) for value in range(1, 4)]
    session.add_all(
        Click(
            id=click_id,
            timestamp=timestamp,
            source=ClickSource.LNKR_APP,
            link_id=link.id,
        )
        for click_id in click_ids
    )
    await session.commit()

    first_page = await click_database.list_clicks_by_link(session, link, limit=2, cursor=None)

    assert [click.id for click in first_page] == [click_ids[2], click_ids[1]]

    cursor = ClickCursor.from_click(first_page[-1])
    second_page = await click_database.list_clicks_by_link(session, link, limit=2, cursor=cursor)

    assert [click.id for click in second_page] == [click_ids[0]]


async def test_list_clicks_by_link__filters_by_link_and_optional_sources(
    session: AsyncSession,
    link: Link,
    link_other: Link,
) -> None:
    session.add_all([link, link_other])
    await session.flush()

    timestamp = datetime.now(tz=UTC)
    trusted_click = Click(
        id=uuid.UUID(int=1),
        timestamp=timestamp,
        source=ClickSource.LNKR_APP,
        link_id=link.id,
    )
    public_click = Click(
        id=uuid.UUID(int=2),
        timestamp=timestamp,
        source=ClickSource.PUBLIC_API,
        link_id=link.id,
    )
    session.add_all(
        [
            trusted_click,
            public_click,
            Click(
                id=uuid.UUID(int=3),
                timestamp=timestamp,
                source=ClickSource.LNKR_APP,
                link_id=link_other.id,
            ),
        ]
    )
    await session.commit()

    all_clicks = await click_database.list_clicks_by_link(session, link, limit=10, cursor=None)
    trusted_clicks = await click_database.list_clicks_by_link(
        session,
        link,
        limit=10,
        cursor=None,
        sources={ClickSource.LNKR_APP},
    )
    no_clicks = await click_database.list_clicks_by_link(
        session,
        link,
        limit=10,
        cursor=None,
        sources=set(),
    )

    assert [click.id for click in all_clicks] == [public_click.id, trusted_click.id]
    assert [click.id for click in trusted_clicks] == [trusted_click.id]
    assert no_clicks == []


async def test_count_clicks_by_links__counts_only_lnkr_app_clicks(
    session: AsyncSession,
    link: Link,
    link_other: Link,
) -> None:
    session.add_all([link, link_other])
    await session.flush()

    session.add_all(
        [
            Click(source=ClickSource.LNKR_APP, link_id=link.id),
            Click(source=ClickSource.LNKR_APP, link_id=link.id),
            Click(source=ClickSource.PUBLIC_API, link_id=link.id),
            Click(source=ClickSource.PUBLIC_API, link_id=link_other.id),
        ]
    )
    await session.commit()

    assert await click_database.count_clicks_by_links(session, []) == {}
    assert await click_database.count_clicks_by_links(session, [link, link_other]) == {link.id: 2}


async def test_count_clicks_by_periods__uses_half_open_ranges_and_lnkr_app_source(
    session: AsyncSession,
    link: Link,
    link_other: Link,
) -> None:
    session.add_all([link, link_other])
    await session.flush()

    start = datetime(2026, 1, 1, tzinfo=UTC)
    session.add_all(
        [
            Click(timestamp=start, source=ClickSource.LNKR_APP, link_id=link.id),  # 1
            Click(timestamp=start + timedelta(days=1), source=ClickSource.LNKR_APP, link_id=link.id),  # 2
            Click(timestamp=start + timedelta(days=2), source=ClickSource.LNKR_APP, link_id=link.id),  # 3
            Click(timestamp=start + timedelta(days=3), source=ClickSource.LNKR_APP, link_id=link.id),  # 4
            Click(timestamp=start + timedelta(days=1), source=ClickSource.PUBLIC_API, link_id=link.id),  # 5
            Click(timestamp=start + timedelta(days=1), source=ClickSource.LNKR_APP, link_id=link_other.id),  # 6
        ]
    )
    await session.commit()
    periods = (
        ClickAnalyticsTimeRange(start=start, end=start + timedelta(days=3)),
        ClickAnalyticsTimeRange(start=start + timedelta(days=1), end=start + timedelta(days=2)),
    )

    assert await click_database.count_clicks_by_periods(session, link, []) == []
    assert await click_database.count_clicks_by_periods(session, link, periods) == [3, 1]  # [1, 2, 3], [2]


async def test_list_daily_click_counts__groups_by_timezone_local_date(session: AsyncSession, link: Link) -> None:
    session.add(link)
    await session.flush()

    session.add_all(
        [
            Click(
                timestamp=datetime(2026, 1, 1, 4, 30, tzinfo=UTC),
                source=ClickSource.LNKR_APP,
                link_id=link.id,
            ),  # 1
            Click(
                timestamp=datetime(2026, 1, 1, 5, 30, tzinfo=UTC),
                source=ClickSource.LNKR_APP,
                link_id=link.id,
            ),  # 2
            Click(
                timestamp=datetime(2026, 1, 2, 4, 30, tzinfo=UTC),
                source=ClickSource.LNKR_APP,
                link_id=link.id,
            ),  # 3
            Click(
                timestamp=datetime(2026, 1, 1, 5, 30, tzinfo=UTC),
                source=ClickSource.PUBLIC_API,
                link_id=link.id,
            ),  # 4
        ]
    )
    await session.commit()
    period = ClickAnalyticsTimeRange(
        start=datetime(2025, 12, 31, 5, tzinfo=UTC),
        end=datetime(2026, 1, 2, 5, tzinfo=UTC),
    )

    daily_counts = await click_database.list_daily_click_counts(session, link, period, "America/New_York")

    assert daily_counts == {
        date(2025, 12, 31): 1,  # 1
        date(2026, 1, 1): 2,  # 2, 3
    }


async def test_list_top_country_click_counts__returns_limited_rows_and_all_known_clicks(
    session: AsyncSession,
    link: Link,
) -> None:
    session.add(link)
    await session.flush()

    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = start + timedelta(days=1)
    session.add_all(
        [
            Click(timestamp=start, source=ClickSource.LNKR_APP, country_code="US", link_id=link.id),  # 1
            Click(timestamp=start, source=ClickSource.LNKR_APP, country_code="US", link_id=link.id),  # 2
            Click(timestamp=start, source=ClickSource.LNKR_APP, country_code="DK", link_id=link.id),  # 3
            Click(timestamp=start, source=ClickSource.LNKR_APP, country_code=None, link_id=link.id),  # 4
            Click(timestamp=start, source=ClickSource.PUBLIC_API, country_code="US", link_id=link.id),  # 5
            Click(timestamp=end, source=ClickSource.LNKR_APP, country_code="US", link_id=link.id),  # 6
        ]
    )
    await session.commit()
    period = ClickAnalyticsTimeRange(start=start, end=end)

    known_country_click_count, top_country_counts = await click_database.list_top_country_click_counts(
        session,
        link,
        period,
        limit=1,
    )
    empty_count, empty_countries = await click_database.list_top_country_click_counts(
        session,
        link,
        ClickAnalyticsTimeRange(start=end + timedelta(days=1), end=end + timedelta(days=2)),
        limit=1,
    )

    assert known_country_click_count == 3  # 1, 2, 3
    assert top_country_counts == [("US", 2)]  # 1, 2
    assert empty_count == 0
    assert empty_countries == []
