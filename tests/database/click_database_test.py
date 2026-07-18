"""
Tests for click database operations.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from lnkr.database import click_database
from lnkr.models import Click, ClickCursor, ClickSource, Link

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from lnkr.models import User


async def test_list_clicks_by_link__cursor_pagination_uses_id_to_break_timestamp_ties(
    session: AsyncSession,
    user: User,
    slug: str,
    target_url: str,
) -> None:
    link = Link(slug=slug, target_url=target_url, user=user)
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

    first_page, has_next = await click_database.list_clicks_by_link(
        session,
        link,
        limit=2,
        cursor=None,
    )

    assert [click.id for click in first_page] == [click_ids[2], click_ids[1]]
    assert has_next is True

    cursor = ClickCursor.from_click(first_page[-1])
    second_page, has_next = await click_database.list_clicks_by_link(
        session,
        link,
        limit=2,
        cursor=cursor,
    )

    assert [click.id for click in second_page] == [click_ids[0]]
    assert has_next is False
