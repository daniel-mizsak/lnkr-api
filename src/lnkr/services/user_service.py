"""
High level database operations for user management.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

from typing import TYPE_CHECKING

from lnkr.database import user_database
from lnkr.exceptions import UserAlreadyExistsError, UserDoesNotExistError
from lnkr.models import User, UserCreate

if TYPE_CHECKING:
    from sqlmodel import Session


def get_or_create_user(session: Session, user_create: UserCreate) -> User:
    """Get or create a user in the database.

    Args:
        session (Session): The database session.
        user_create (UserCreate): The data model for creating a user.

    Returns:
        User: User object.
    """
    try:
        return get_user(session, user_create.email)
    except UserDoesNotExistError:
        return _create_user(session, user_create)


def get_user(session: Session, email: str) -> User:
    """Get a user from the database by its email.

    Args:
        session (Session): The database session.
        email (str): The email of the user.

    Raises:
        UserDoesNotExistError: If the user does not exist in the database.

    Returns:
        User: User object.
    """
    user = user_database.get_user_by_email(session, email)
    if user is None:
        raise UserDoesNotExistError(email=email)
    return user


def _create_user(session: Session, user_create: UserCreate) -> User:
    if user_database.get_user_by_email(session, user_create.email) is not None:
        raise UserAlreadyExistsError(email=user_create.email)
    return user_database.add_user(session, User.from_user_create(user_create))
