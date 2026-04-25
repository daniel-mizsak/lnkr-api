"""
High level services for click management.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING

from sqlalchemy.exc import SQLAlchemyError

from lnkr.database import click_database
from lnkr.models import Click, ClickCreate, Link

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession


async def create_click(session: AsyncSession, click_create: ClickCreate, link_id: uuid.UUID) -> Click:
    """Create a click in the database."""
    click = Click.from_click_create(click_create, link_id)

    try:
        await click_database.save_click(session, click)
        await session.commit()
        await session.refresh(click)
    except SQLAlchemyError:
        await session.rollback()
        raise

    return click


async def list_clicks(session: AsyncSession, link: Link, per_page: int, page: int) -> list[Click]:
    """List all clicks for a given link."""
    per_page = min(per_page, 100)
    return await click_database.list_clicks_by_link(session, link, per_page, page)
