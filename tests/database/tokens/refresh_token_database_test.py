"""
Tests for refresh token database operations.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
import time_machine
from sqlalchemy import select

from lnkr.database.tokens import refresh_token_database
from lnkr.models import RefreshToken

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from lnkr.models import User


@pytest.mark.usefixtures("frozen_now")
async def test_consume_refresh_token__single_use(
    session: AsyncSession,
    user: User,
    now: datetime,
    expires_at: datetime,
) -> None:
    refresh_token = RefreshToken(
        user_id=user.id,
        token_hash="a" * 64,
        expires_at=expires_at,
    )
    session.add(refresh_token)
    await session.commit()

    consumed = await refresh_token_database.consume_refresh_token(session, refresh_token.token_hash)
    consumed_again = await refresh_token_database.consume_refresh_token(session, refresh_token.token_hash)

    assert consumed is not None
    assert consumed.used_at == now
    assert consumed_again is None


@pytest.mark.usefixtures("frozen_now")
async def test_revoke_refresh_token__prevents_consumption(
    session: AsyncSession,
    user: User,
    now: datetime,
    expires_at: datetime,
) -> None:
    refresh_token = RefreshToken(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash="a" * 64,
        expires_at=expires_at,
    )
    session.add(refresh_token)
    await session.commit()

    revoked = await refresh_token_database.revoke_refresh_token(session, refresh_token.token_hash)
    revoked_again = await refresh_token_database.revoke_refresh_token(session, refresh_token.token_hash)
    consumed = await refresh_token_database.consume_refresh_token(session, refresh_token.token_hash)

    assert revoked is not None
    assert revoked.revoked_at == now
    assert revoked_again is None
    assert consumed is None


@pytest.mark.parametrize(
    ("expires_in", "used_at", "revoked_at"),
    [
        pytest.param(timedelta(microseconds=-1), None, None, id="expired"),
        pytest.param(timedelta(0), None, None, id="expires-now"),
        pytest.param(timedelta(minutes=1), datetime(2026, 1, 1, tzinfo=UTC), None, id="used"),
        pytest.param(timedelta(minutes=1), None, datetime(2026, 1, 1, tzinfo=UTC), id="revoked"),
    ],
)
async def test_clean_up_refresh_tokens__deletes_only_expired_used_or_revoked_tokens_without_commit(
    session: AsyncSession,
    user: User,
    expires_in: timedelta,
    used_at: datetime | None,
    revoked_at: datetime | None,
    now: datetime,
) -> None:
    obsolete_token = RefreshToken(
        token_hash="a" * 64,
        user_id=user.id,
        expires_at=now + expires_in,
        used_at=used_at,
        revoked_at=revoked_at,
    )
    valid_token = RefreshToken(token_hash="b" * 64, user_id=user.id, expires_at=now + timedelta(microseconds=1))
    session.add_all([obsolete_token, valid_token])
    await session.commit()
    token_ids = {obsolete_token.id, valid_token.id}

    with time_machine.travel(now, tick=False):
        await refresh_token_database.clean_up_refresh_tokens(session)

    assert list((await session.scalars(select(RefreshToken.id))).all()) == [valid_token.id]

    await session.rollback()
    assert set((await session.scalars(select(RefreshToken.id))).all()) == token_ids


async def test_consume_refresh_token__immediately_before_expiration(
    session: AsyncSession,
    user: User,
    expires_at: datetime,
) -> None:
    token = RefreshToken(user_id=user.id, token_hash="a" * 64, expires_at=expires_at)
    session.add(token)
    await session.commit()

    with time_machine.travel(expires_at - timedelta(microseconds=1), tick=False):
        consumed_token = await refresh_token_database.consume_refresh_token(session, token.token_hash)

    assert consumed_token is token


@pytest.mark.parametrize(
    "elapsed",
    [pytest.param(timedelta(0), id="at-expiration"), pytest.param(timedelta(microseconds=1), id="after-expiration")],
)
async def test_consume_refresh_token__expired_token(session: AsyncSession, user: User, elapsed: timedelta) -> None:
    expires_at = datetime(2026, 1, 1, tzinfo=UTC)
    token = RefreshToken(
        user_id=user.id,
        token_hash="a" * 64,
        expires_at=expires_at,
    )
    session.add(token)
    await session.commit()

    with time_machine.travel(expires_at + elapsed, tick=False):
        consumed_token = await refresh_token_database.consume_refresh_token(session, token.token_hash)

    assert consumed_token is None
    await session.refresh(token)
    assert token.used_at is None


@pytest.mark.parametrize(
    "elapsed",
    [pytest.param(timedelta(0), id="at-expiration"), pytest.param(timedelta(microseconds=1), id="after-expiration")],
)
async def test_revoke_refresh_token__expired_token(session: AsyncSession, user: User, elapsed: timedelta) -> None:
    expires_at = datetime(2026, 1, 1, tzinfo=UTC)
    token = RefreshToken(
        user_id=user.id,
        token_hash="a" * 64,
        expires_at=expires_at,
    )
    session.add(token)
    await session.commit()

    with time_machine.travel(expires_at + elapsed, tick=False):
        revoked_token = await refresh_token_database.revoke_refresh_token(session, token.token_hash)

    assert revoked_token is None
    await session.refresh(token)
    assert token.revoked_at is None


async def test_revoke_refresh_token__immediately_before_expiration(
    session: AsyncSession,
    user: User,
    expires_at: datetime,
) -> None:
    token = RefreshToken(user_id=user.id, token_hash="a" * 64, expires_at=expires_at)
    session.add(token)
    await session.commit()

    with time_machine.travel(expires_at - timedelta(microseconds=1), tick=False):
        revoked_token = await refresh_token_database.revoke_refresh_token(session, token.token_hash)

    assert revoked_token is token
