"""
High level database operations for user management.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

from typing import TYPE_CHECKING

from sqlalchemy.exc import IntegrityError

from lnkr.database import user_database
from lnkr.exceptions import UserAlreadyExistsError, UserDoesNotExistError
from lnkr.models import User, UserCreate

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def get_or_create_user(session: AsyncSession, user_create: UserCreate) -> User:
    """Get or create a user in the database.

    Args:
        session (AsyncSession): The database session.
        user_create (UserCreate): The data model for creating a user.

    Returns:
        User: User object.
    """
    try:
        return await get_user(session, user_create.email)
    except UserDoesNotExistError:
        try:
            return await _create_user(session, user_create)
        except UserAlreadyExistsError:
            return await get_user(session, user_create.email)


async def get_user(session: AsyncSession, email: str) -> User:
    """Get a user from the database by its email.

    Args:
        session (AsyncSession): The database session.
        email (str): The email of the user.

    Raises:
        UserDoesNotExistError: If the user does not exist in the database.

    Returns:
        User: User object.
    """
    user = await user_database.get_user_by_email(session, email)
    if user is None:
        raise UserDoesNotExistError(email=email)
    return user


async def _create_user(session: AsyncSession, user_create: UserCreate) -> User:
    try:
        return await user_database.add_user(session, User.from_user_create(user_create))
    except IntegrityError as integrity_error:
        await session.rollback()
        raise UserAlreadyExistsError(email=user_create.email) from integrity_error
