"""
Database initialization and session management.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from lnkr.config import Environment, settings
from lnkr.models import UserCreate
from lnkr.models.base import Base
from lnkr.services.user_service import get_or_create_user

engine = create_engine(str(settings.DATABASE_URL), pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_database() -> None:
    """Create database and tables."""
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as session:
        if settings.ENVIRONMENT == Environment.DEVELOPMENT:
            get_or_create_user(session, UserCreate(email=settings.DEVELOPMENT_USER_EMAIL))
