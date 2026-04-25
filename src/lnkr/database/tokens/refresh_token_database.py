"""
Low level database operations for refresh token management.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import update

from lnkr.models import RefreshToken

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def save_refresh_token(session: AsyncSession, refresh_token: RefreshToken) -> RefreshToken:
    """Persist a refresh token without committing the transaction."""
    session.add(refresh_token)
    await session.flush()
    return refresh_token


async def consume_refresh_token(session: AsyncSession, token_hash: str) -> RefreshToken | None:
    """Atomically mark a valid refresh token as used and return it."""
    now = datetime.now(tz=UTC)

    statement = (
        update(RefreshToken)
        .where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.used_at.is_(None),
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > now,
        )
        .values(used_at=now)
        .returning(RefreshToken)
    )

    result = await session.execute(statement)
    return result.scalars().first()


async def revoke_refresh_token(session: AsyncSession, token_hash: str) -> RefreshToken | None:
    """Atomically mark a valid refresh token as revoked and return it."""
    now = datetime.now(tz=UTC)

    statement = (
        update(RefreshToken)
        .where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.used_at.is_(None),
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > now,
        )
        .values(revoked_at=now)
        .returning(RefreshToken)
    )

    result = await session.execute(statement)
    return result.scalars().first()
