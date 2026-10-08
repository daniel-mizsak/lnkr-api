"""
FastAPI dependency that provides the database session.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

import logging
from typing import TYPE_CHECKING

from sqlalchemy.exc import SQLAlchemyError

from lnkr.database import AsyncSessionLocal

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def get_session() -> AsyncGenerator[AsyncSession]:
    """Get session for database operations."""
    try:
        async with AsyncSessionLocal() as session:
            yield session
    except SQLAlchemyError:
        logger.exception("database.session_error")
        raise
