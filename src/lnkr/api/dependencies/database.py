"""
FastAPI dependency that provides the database session.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from lnkr.database import engine

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


async def get_session() -> AsyncGenerator[AsyncSession]:
    """Get session for database operations."""
    async with AsyncSession(engine) as session:
        yield session
