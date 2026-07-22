"""
Tests for login token database operations.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from lnkr.database.tokens import login_token_database
from lnkr.models import LoginToken

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def test_consume_login_token__is_atomic_and_single_use(session: AsyncSession, email: str) -> None:
    login_token = LoginToken(
        token_hash="a" * 64,
        email=email,
        expires_at=datetime.now(tz=UTC) + timedelta(minutes=1),
    )
    session.add(login_token)
    await session.commit()

    consumed = await login_token_database.consume_login_token(session, login_token.token_hash)
    consumed_again = await login_token_database.consume_login_token(session, login_token.token_hash)

    assert consumed is not None
    assert consumed.used_at is not None
    assert consumed_again is None


async def test_consume_login_token__rejects_expired_token(session: AsyncSession, email: str) -> None:
    login_token = LoginToken(
        token_hash="b" * 64,
        email=email,
        expires_at=datetime.now(tz=UTC) - timedelta(seconds=1),
    )
    session.add(login_token)
    await session.commit()

    assert await login_token_database.consume_login_token(session, login_token.token_hash) is None
