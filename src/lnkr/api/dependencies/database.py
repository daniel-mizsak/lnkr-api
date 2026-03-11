"""
FastAPI dependency that provides the database session.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

from typing import TYPE_CHECKING

from lnkr.database import SessionLocal

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from sqlalchemy.ext.asyncio import AsyncSession


async def get_session() -> AsyncGenerator[AsyncSession]:
    """Get session for database operations."""
    async with SessionLocal() as session:
        yield session
