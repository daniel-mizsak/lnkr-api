"""
Low level database operations for link management.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING, Literal

from sqlalchemy import func, select

from lnkr.models import Link, User

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession


async def save_link(session: AsyncSession, link: Link) -> Link:
    """Persist a link without committing the transaction."""
    session.add(link)
    await session.flush()
    return link


async def get_link_by_slug(session: AsyncSession, slug: str) -> Link | None:
    """Get link from database by slug."""
    result = await session.execute(select(Link).where(Link.slug == slug).limit(1))
    return result.scalars().first()


async def delete_link(session: AsyncSession, link: Link) -> None:
    """Delete link from database without committing the transaction."""
    await session.delete(link)
    await session.flush()


async def count_links_by_user(session: AsyncSession, user_id: uuid.UUID) -> int:
    """Count the number of links owned by a user."""
    statement = select(func.count()).where(Link.user_id == user_id)
    result = await session.execute(statement)
    return result.scalar_one()


async def list_links_by_user(
    session: AsyncSession,
    user: User,
    sort: Literal["created_at", "updated_at"],
    direction: Literal["ascending", "descending"],
    per_page: int,
    page: int,
) -> list[Link]:
    """List all links owned by a user."""
    offset = (page - 1) * per_page

    sort_column = Link.created_at if sort == "created_at" else Link.updated_at
    order_clause = sort_column.asc() if direction == "ascending" else sort_column.desc()

    statement = (
        select(Link)
        .where(Link.user_id == user.id)
        .order_by(order_clause, Link.id.desc())
        .offset(offset)
        .limit(per_page)
    )
    result = await session.execute(statement)
    return list(result.scalars().all())
