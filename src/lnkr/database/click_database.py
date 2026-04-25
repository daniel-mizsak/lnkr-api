"""
Low level database operations for click management.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING

from sqlalchemy import select

from lnkr.models import Click, Link

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def save_click(session: AsyncSession, click: Click) -> Click:
    """Persist a click without committing the transaction."""
    session.add(click)
    await session.flush()
    return click


async def list_clicks_by_link(session: AsyncSession, link: Link, per_page: int, page: int) -> list[Click]:
    """List all clicks for a link."""
    offset = (page - 1) * per_page
    statement = (
        select(Click)
        .where(Click.link_id == link.id)
        .order_by(Click.timestamp.desc(), Click.id.desc())
        .offset(offset)
        .limit(per_page)
    )
    result = await session.execute(statement)
    return list(result.scalars().all())
