"""
High level services for user management.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING

from sqlalchemy.exc import IntegrityError

from lnkr.database import user_database
from lnkr.exceptions import UserDoesNotExistError
from lnkr.models import User, UserCreate

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession


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


async def get_or_create_user_without_commit(session: AsyncSession, user_create: UserCreate) -> User:
    """Get or create a user without committing; the caller owns the transaction."""
    existing_user = await user_database.get_user_by_email(session, user_create.email)
    if existing_user is not None:
        return existing_user

    user = User.from_user_create(user_create)

    try:
        async with session.begin_nested():
            await user_database.save_user(session, user)
    except IntegrityError:
        return await get_user_by_email(session, user_create.email)

    return user
