"""
Tests for cleaning up unnecessary database entries.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from unittest import mock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from lnkr import cleanup
from lnkr.models import LoginToken, RefreshToken

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from lnkr.models import User


@pytest.mark.usefixtures("frozen_now")
async def test_clean_up__commits_token_deletions_and_preserves_valid_tokens(
    session: AsyncSession,
    user: User,
    now: datetime,
) -> None:
    expired_login_token = LoginToken(token_hash="a" * 64, email=user.email, expires_at=now - timedelta(minutes=1))
    valid_login_token = LoginToken(token_hash="b" * 64, email=user.email, expires_at=now + timedelta(minutes=1))
    expired_refresh_token = RefreshToken(token_hash="c" * 64, user_id=user.id, expires_at=now - timedelta(minutes=1))
    valid_refresh_token = RefreshToken(token_hash="d" * 64, user_id=user.id, expires_at=now + timedelta(minutes=1))
    session.add_all([expired_login_token, valid_login_token, expired_refresh_token, valid_refresh_token])
    await session.commit()

    # Let cleanup manage its own session and transaction against the test database.
    with (
        mock.patch.object(cleanup, "AsyncSessionLocal", async_sessionmaker(session.bind, expire_on_commit=False)),
        mock.patch.object(cleanup, "engine") as engine,
    ):
        engine.dispose = mock.AsyncMock()

        await cleanup._clean_up()  # noqa: SLF001

    assert list((await session.scalars(select(LoginToken.id))).all()) == [valid_login_token.id]
    assert list((await session.scalars(select(RefreshToken.id))).all()) == [valid_refresh_token.id]
    engine.dispose.assert_awaited_once_with()


@pytest.mark.usefixtures("frozen_now")
async def test_clean_up__refresh_failure_rolls_back_all_changes(
    session: AsyncSession,
    user: User,
    now: datetime,
) -> None:
    expires_at = now - timedelta(minutes=1)
    login_token = LoginToken(token_hash="a" * 64, email=user.email, expires_at=expires_at)
    refresh_token = RefreshToken(token_hash="b" * 64, user_id=user.id, expires_at=expires_at)
    session.add_all([login_token, refresh_token])
    await session.commit()
    clean_up_refresh_tokens = cleanup.clean_up_refresh_tokens

    async def fail_after_refresh_cleanup(cleanup_session: AsyncSession) -> None:
        await clean_up_refresh_tokens(cleanup_session)
        assert list((await cleanup_session.scalars(select(LoginToken.id))).all()) == []
        assert list((await cleanup_session.scalars(select(RefreshToken.id))).all()) == []
        message = "Refresh token cleanup failed"
        raise RuntimeError(message)

    with (
        mock.patch.object(cleanup, "AsyncSessionLocal", async_sessionmaker(session.bind, expire_on_commit=False)),
        mock.patch.object(cleanup, "engine") as engine,
        mock.patch.object(cleanup, "clean_up_refresh_tokens", fail_after_refresh_cleanup),
    ):
        engine.dispose = mock.AsyncMock()

        with pytest.raises(RuntimeError, match="Refresh token cleanup failed"):
            await cleanup._clean_up()  # noqa: SLF001

    assert list((await session.scalars(select(LoginToken.id))).all()) == [login_token.id]
    assert list((await session.scalars(select(RefreshToken.id))).all()) == [refresh_token.id]
    engine.dispose.assert_awaited_once_with()
