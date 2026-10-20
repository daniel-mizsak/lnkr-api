"""
Low level database operations for login token management.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import delete, select, update

from lnkr.models import LoginToken

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def save_login_token(session: AsyncSession, login_token: LoginToken) -> LoginToken:
    """Persist a login token without committing the transaction."""
    session.add(login_token)
    await session.flush()
    return login_token


async def get_login_token_by_hash(session: AsyncSession, token_hash: str) -> LoginToken | None:
    """Look up a login token without locking it."""
    result = await session.execute(select(LoginToken).where(LoginToken.token_hash == token_hash))
    return result.scalar_one_or_none()


async def consume_login_token(session: AsyncSession, token_hash: str) -> LoginToken | None:
    """Atomically mark a valid login token as used and return it."""
    now = datetime.now(tz=UTC)

    statement = (
        update(LoginToken)
        .where(
            LoginToken.token_hash == token_hash,
            LoginToken.used_at.is_(None),
            LoginToken.expires_at > now,
        )
        .values(used_at=now)
        .returning(LoginToken)
    )

    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def delete_login_tokens_by_email(session: AsyncSession, email: str) -> None:
    """Delete all login tokens for a given email without committing the transaction."""
    statement = delete(LoginToken).where(LoginToken.email == email)
    await session.execute(statement)


async def clean_up_login_tokens(session: AsyncSession) -> None:
    """Delete all expired or used login tokens without committing the transaction."""
    now = datetime.now(tz=UTC)
    statement = delete(LoginToken).where((LoginToken.expires_at <= now) | (LoginToken.used_at.is_not(None)))
    await session.execute(statement)
