"""
Database initialization and session management.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from sqlalchemy import URL
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from lnkr.config.database_settings import database_settings

engine = create_async_engine(
    URL.create(
        drivername="postgresql+psycopg",
        username=database_settings.POSTGRES_USERNAME,
        password=database_settings.POSTGRES_PASSWORD.get_secret_value(),
        host=database_settings.POSTGRES_HOST,
        port=database_settings.POSTGRES_PORT,
        database=database_settings.POSTGRES_DATABASE,
    ),
    pool_pre_ping=True,
)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
