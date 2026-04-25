"""
High level services for user management.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from lnkr.database import user_database
from lnkr.exceptions import UserAlreadyExistsError, UserDoesNotExistError
from lnkr.models import User, UserCreate

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession


async def get_or_create_user(session: AsyncSession, user_create: UserCreate) -> User:
    """Get or create a user in the database."""
    try:
        return await _create_user(session, user_create)
    except UserAlreadyExistsError:
        return await get_user_by_email(session, user_create.email)


async def get_user_by_id(session: AsyncSession, user_id: uuid.UUID) -> User:
    """Get a user from the database by id."""
    user = await user_database.get_user_by_id(session, user_id)
    if user is None:
        raise UserDoesNotExistError.by_id(user_id=user_id)
    return user


async def get_user_by_email(session: AsyncSession, email: str) -> User:
    """Get a user from the database by email."""
    user = await user_database.get_user_by_email(session, email)
    if user is None:
        raise UserDoesNotExistError.by_email(email=email)
    return user


async def _create_user(session: AsyncSession, user_create: UserCreate) -> User:
    user = User.from_user_create(user_create)

    try:
        await user_database.save_user(session, user)
        await session.commit()
    except IntegrityError as integrity_error:
        await session.rollback()
        raise UserAlreadyExistsError(email=user_create.email) from integrity_error
    except SQLAlchemyError:
        await session.rollback()
        raise

    await session.refresh(user)
    return user
