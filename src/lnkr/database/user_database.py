"""
Low level database operations for user management.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING

from sqlalchemy import select

from lnkr.models import User

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession


async def save_user(session: AsyncSession, user: User) -> User:
    """Persist a user without committing the transaction."""
    session.add(user)
    await session.flush()
    return user


async def get_user_by_id_for_update(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    """Get and lock a user row for update."""
    result = await session.execute(select(User).where(User.id == user_id).with_for_update())
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    """Get user from database by id."""
    result = await session.execute(select(User).where(User.id == user_id).limit(1))
    return result.scalars().first()


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    """Get user from database by email."""
    result = await session.execute(select(User).where(User.email == email).limit(1))
    return result.scalars().first()
