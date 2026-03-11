"""
Low level database operations for user management.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

from typing import TYPE_CHECKING

from sqlalchemy import select

from lnkr.models import User

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def add_user(session: Session, user: User) -> User:
    """Add user to database."""
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def get_user_by_email(session: Session, email: str) -> User | None:
    """Get user from database by user email."""
    result = session.execute(select(User).where(User.email == email).limit(1))
    return result.scalars().first()
