"""
Tests for refresh token database operations.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest import mock

import pytest
from sqlalchemy import select

from lnkr.database.tokens import refresh_token_database
from lnkr.models import RefreshToken

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from lnkr.models import User


async def test_consume_refresh_token__is_atomic_and_single_use(session: AsyncSession, user: User) -> None:
    refresh_token = RefreshToken(
        user_id=user.id,
        token_hash="c" * 64,
        expires_at=datetime.now(tz=UTC) + timedelta(minutes=1),
    )
    session.add(refresh_token)
    await session.commit()

    consumed = await refresh_token_database.consume_refresh_token(session, refresh_token.token_hash)
    consumed_again = await refresh_token_database.consume_refresh_token(session, refresh_token.token_hash)

    assert consumed is not None
    assert consumed.used_at is not None
    assert consumed_again is None


async def test_revoke_refresh_token__prevents_consumption(session: AsyncSession, user: User) -> None:
    refresh_token = RefreshToken(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash="d" * 64,
        expires_at=datetime.now(tz=UTC) + timedelta(minutes=1),
    )
    session.add(refresh_token)
    await session.commit()

    revoked = await refresh_token_database.revoke_refresh_token(session, refresh_token.token_hash)
    revoked_again = await refresh_token_database.revoke_refresh_token(session, refresh_token.token_hash)
    consumed = await refresh_token_database.consume_refresh_token(session, refresh_token.token_hash)

    assert revoked is not None
    assert revoked.revoked_at is not None
    assert revoked_again is None
    assert consumed is None


@pytest.mark.parametrize(
    ("expires_in", "used_at", "revoked_at"),
    [
        pytest.param(timedelta(seconds=-1), None, None, id="expired"),
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
) -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    obsolete_token = RefreshToken(
        token_hash="a" * 64,
        user_id=user.id,
        expires_at=now + expires_in,
        used_at=used_at,
        revoked_at=revoked_at,
    )
    valid_token = RefreshToken(token_hash="b" * 64, user_id=user.id, expires_at=now + timedelta(seconds=1))
    session.add_all([obsolete_token, valid_token])
    await session.commit()
    token_ids = {obsolete_token.id, valid_token.id}

    with mock.patch.object(refresh_token_database, "datetime") as clock:
        clock.now.return_value = now
        await refresh_token_database.clean_up_refresh_tokens(session)

    assert list((await session.scalars(select(RefreshToken.id))).all()) == [valid_token.id]

    await session.rollback()
    assert set((await session.scalars(select(RefreshToken.id))).all()) == token_ids
