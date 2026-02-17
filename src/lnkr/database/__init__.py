"""
Database initialization and session management.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

from sqlmodel import Session, SQLModel, create_engine

from lnkr.config import Environment, settings
from lnkr.models import UserCreate
from lnkr.services.user_service import get_or_create_user

engine = create_engine(str(settings.DATABASE_URL), pool_pre_ping=True)


def create_database() -> None:
    """Create database and tables."""
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        if settings.ENVIRONMENT == Environment.DEVELOPMENT:
            get_or_create_user(session, UserCreate(email=settings.DEVELOPMENT_USER_EMAIL))
