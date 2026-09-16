"""
High level services for user management.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

import contextlib
from typing import TYPE_CHECKING

from redis.exceptions import RedisError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from lnkr.cache import link_cache
from lnkr.database import link_database, user_database
from lnkr.database.tokens import login_token_database
from lnkr.exceptions import UserDoesNotExistError
from lnkr.models import User, UserCreate

if TYPE_CHECKING:
    import uuid

    from redis.asyncio import Redis
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


async def delete_user(session: AsyncSession, cache: Redis, user: User) -> None:
    """Delete a user from the database."""
    user_id = user.id
    try:
        locked_user = await user_database.get_user_by_id_for_update(session, user_id)
        if locked_user is None:
            await session.rollback()
            raise UserDoesNotExistError.by_id(user_id=user_id)

        slugs = await link_database.get_link_slugs_by_user(session, user_id)
        await login_token_database.delete_login_tokens_by_email(session, locked_user.email)
        await user_database.delete_user(session, locked_user)
        await session.commit()
    except SQLAlchemyError:
        await session.rollback()
        raise

    with contextlib.suppress(RedisError):
        await link_cache.set_cached_links_invalidated(cache, slugs)
