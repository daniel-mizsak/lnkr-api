"""
Low level database operations for user management.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

from typing import TYPE_CHECKING

from sqlalchemy import select

from lnkr.models import User

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def add_user(session: AsyncSession, user: User) -> User:
    """Add user to database."""
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    """Get user from database by user email."""
    result = await session.execute(select(User).where(User.email == email).limit(1))
    return result.scalars().first()
