"""
Low level database operations for click management.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING

from sqlalchemy import and_, or_, select

from lnkr.models import Click, ClickCursor, ClickSource, Link

if TYPE_CHECKING:
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
