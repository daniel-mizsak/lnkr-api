"""
Database initialization and session management.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from lnkr.config import Environment, settings
from lnkr.models import UserCreate
from lnkr.models.base import Base
from lnkr.services.user_service import get_or_create_user

engine = create_async_engine(str(settings.DATABASE_URL), pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def create_database() -> None:
    """Create database and tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        if settings.ENVIRONMENT == Environment.DEVELOPMENT:
            await get_or_create_user(session, UserCreate(email=settings.DEVELOPMENT_USER_EMAIL))
