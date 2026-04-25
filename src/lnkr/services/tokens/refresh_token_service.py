"""
High level services for refresh token management.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from lnkr.config.application_settings import application_settings
from lnkr.database.tokens import refresh_token_database
from lnkr.exceptions import RefreshTokenInvalidError
from lnkr.models import RefreshToken

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession


async def create_and_save_refresh_token(session: AsyncSession, user_id: uuid.UUID) -> str:
    """Create a refresh token and save it to the database."""
    try:
        refresh_token_value = await _create_refresh_token_without_commit(session, user_id)
        # TODO: Handle RuntimeError.
        await session.commit()
    except SQLAlchemyError:
        await session.rollback()
        raise

    return refresh_token_value


async def rotate_refresh_token(session: AsyncSession, refresh_token_value: str) -> tuple[uuid.UUID, str]:
    """Consume a refresh token and issue a replacement refresh token."""
    token_hash = _hash_token(refresh_token_value)

    try:
        refresh_token = await refresh_token_database.consume_refresh_token(session, token_hash)
        if refresh_token is None:
            await session.rollback()
            raise RefreshTokenInvalidError

        new_refresh_token_value = await _create_refresh_token_without_commit(session, refresh_token.user_id)
        # TODO: Handle RuntimeError.
        await session.commit()
    except SQLAlchemyError:
        await session.rollback()
        raise

    return refresh_token.user_id, new_refresh_token_value


async def revoke_refresh_token(session: AsyncSession, refresh_token_value: str) -> None:
    """Validate and revoke a refresh token."""
    token_hash = _hash_token(refresh_token_value)

    try:
        refresh_token = await refresh_token_database.revoke_refresh_token(session, token_hash)
        if refresh_token is None:
            await session.rollback()
            raise RefreshTokenInvalidError

        await session.commit()
    except SQLAlchemyError:
        await session.rollback()
        raise


async def _create_refresh_token_without_commit(session: AsyncSession, user_id: uuid.UUID) -> str:
    maximum_unique_refresh_token_generation_attempts = 5

    for _ in range(maximum_unique_refresh_token_generation_attempts):
        refresh_token_value = secrets.token_urlsafe(32)
        token_hash = _hash_token(refresh_token_value)

        try:
            async with session.begin_nested():
                expires_at = datetime.now(tz=UTC) + timedelta(days=application_settings.REFRESH_TOKEN_EXPIRE_DAYS)
                await refresh_token_database.save_refresh_token(
                    session,
                    RefreshToken.from_user_id(user_id, token_hash, expires_at),
                )
        except IntegrityError:
            continue
        else:
            return refresh_token_value

    msg = "Failed to generate a unique refresh token after multiple attempts."
    raise RuntimeError(msg)


def _hash_token(token_value: str) -> str:
    return hashlib.sha256(token_value.encode()).hexdigest()
