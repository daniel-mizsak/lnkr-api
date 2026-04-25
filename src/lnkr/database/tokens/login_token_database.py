"""
Low level database operations for login token management.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import update

from lnkr.models import LoginToken

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def save_login_token(session: AsyncSession, login_token: LoginToken) -> LoginToken:
    """Persist a login token without committing the transaction."""
    session.add(login_token)
    await session.flush()
    return login_token


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
    return result.scalars().first()
