"""
FastAPI dependency that provides the database session.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from lnkr.database import engine

if TYPE_CHECKING:
    from collections.abc import Generator


def get_session() -> Generator[Session]:
    """Get session for database operations."""
    with Session(engine) as session:
        yield session
