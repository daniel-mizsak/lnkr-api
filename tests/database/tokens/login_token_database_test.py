"""
Tests for login token database operations.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
import time_machine
from sqlalchemy import select

from lnkr.database.tokens import login_token_database
from lnkr.models import LoginToken

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.usefixtures("frozen_now")
async def test_consume_login_token__single_use(
    session: AsyncSession,
    email: str,
    now: datetime,
    expires_at: datetime,
) -> None:
    login_token = LoginToken(
        token_hash="a" * 64,
        email=email,
        expires_at=expires_at,
    )
    session.add(login_token)
    await session.commit()

    consumed = await login_token_database.consume_login_token(session, login_token.token_hash)
    consumed_again = await login_token_database.consume_login_token(session, login_token.token_hash)

    assert consumed is not None
    assert consumed.used_at == now
    assert consumed_again is None


async def test_consume_login_token__immediately_before_expiration(
    session: AsyncSession,
    email: str,
    expires_at: datetime,
) -> None:
    token = LoginToken(email=email, token_hash="a" * 64, expires_at=expires_at)
    session.add(token)
    await session.commit()

    with time_machine.travel(expires_at - timedelta(microseconds=1), tick=False):
        consumed_token = await login_token_database.consume_login_token(session, token.token_hash)

    assert consumed_token is token


@pytest.mark.parametrize(
    "elapsed",
    [pytest.param(timedelta(0), id="at-expiration"), pytest.param(timedelta(microseconds=1), id="after-expiration")],
)
async def test_consume_login_token__expired_token(session: AsyncSession, email: str, elapsed: timedelta) -> None:
    expires_at = datetime(2026, 1, 1, tzinfo=UTC)
    token = LoginToken(
        email=email,
        token_hash="a" * 64,
        expires_at=expires_at,
    )
    session.add(token)
    await session.commit()

    with time_machine.travel(expires_at + elapsed, tick=False):
        consumed_token = await login_token_database.consume_login_token(session, token.token_hash)

    assert consumed_token is None
    await session.refresh(token)
    assert token.used_at is None


async def test_delete_login_tokens_by_email__deletes_only_matching_tokens(
    session: AsyncSession,
    email: str,
    now: datetime,
) -> None:
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


@pytest.mark.parametrize(
    ("expires_in", "used_at"),
    [
        pytest.param(timedelta(microseconds=-1), None, id="expired"),
        pytest.param(timedelta(0), None, id="expires-now"),
        pytest.param(timedelta(minutes=1), datetime(2026, 1, 1, tzinfo=UTC), id="used"),
    ],
)
async def test_clean_up_login_tokens__deletes_only_expired_or_used_tokens_without_commit(
    session: AsyncSession,
    email: str,
    expires_in: timedelta,
    used_at: datetime | None,
    now: datetime,
) -> None:
    obsolete_token = LoginToken(token_hash="a" * 64, email=email, expires_at=now + expires_in, used_at=used_at)
    valid_token = LoginToken(token_hash="b" * 64, email=email, expires_at=now + timedelta(microseconds=1))
    session.add_all([obsolete_token, valid_token])
    await session.commit()
    token_ids = {obsolete_token.id, valid_token.id}

    with time_machine.travel(now, tick=False):
        await login_token_database.clean_up_login_tokens(session)

    assert list((await session.scalars(select(LoginToken.id))).all()) == [valid_token.id]

    await session.rollback()
    assert set((await session.scalars(select(LoginToken.id))).all()) == token_ids
