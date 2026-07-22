"""
Tests for refresh token database operations.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

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
