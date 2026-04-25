"""
FastAPI dependency that provides the database session.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING

from lnkr.database import AsyncSessionLocal

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from sqlalchemy.ext.asyncio import AsyncSession


async def get_session() -> AsyncGenerator[AsyncSession]:
    """Get session for database operations."""
    async with AsyncSessionLocal() as session:
        yield session
