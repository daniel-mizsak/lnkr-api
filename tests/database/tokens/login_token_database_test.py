"""
Tests for login token database operations.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import select

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


async def test_delete_login_tokens_by_email__deletes_only_matching_tokens(session: AsyncSession, email: str) -> None:
    now = datetime.now(tz=UTC)
    tokens = [
        LoginToken(token_hash="a" * 64, email=email, expires_at=now + timedelta(minutes=10)),
        LoginToken(token_hash="b" * 64, email=email, expires_at=now + timedelta(minutes=1), used_at=now),
        LoginToken(token_hash="c" * 64, email=email, expires_at=now - timedelta(minutes=10)),
        LoginToken(token_hash="d" * 64, email=f"other_{email}", expires_at=now + timedelta(minutes=1)),
    ]
    session.add_all(tokens)
    await session.commit()
    other_token_id = tokens[-1].id

    await login_token_database.delete_login_tokens_by_email(session, email)

    assert list((await session.scalars(select(LoginToken.id))).all()) == [other_token_id]
