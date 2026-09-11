"""
Tests for the login token service.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

import hashlib
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest import mock

import pytest
from sqlalchemy import select

from lnkr.database import user_database
from lnkr.exceptions import LoginTokenGenerationError, RefreshTokenGenerationError
from lnkr.models import IpAddress, LoginToken, LoginTokenCreate, RefreshToken, UserAgent
from lnkr.services.tokens import login_token_service, refresh_token_service

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from lnkr.models import User


async def test_create_and_save_login_token__generation_attempts_exhausted(
    session: AsyncSession,
    email: str,
) -> None:
    generated_character = "A"
    login_token_value = generated_character * login_token_service.LOGIN_TOKEN_LENGTH
    session.add(
        LoginToken(
            email=email,
            token_hash=hashlib.sha256(login_token_value.encode()).hexdigest(),
            expires_at=datetime.now(tz=UTC) + timedelta(minutes=10),
        ),
    )
    await session.commit()

    with (
        mock.patch.object(login_token_service.secrets, "choice", mock.Mock(return_value=generated_character)),
        pytest.raises(LoginTokenGenerationError),
    ):
        await login_token_service.create_and_save_login_token(
            session,
            LoginTokenCreate(email=email),
            IpAddress(),
            None,
            UserAgent(),
        )


async def test_authenticate_with_login_token__refresh_failure_rolls_back_all_changes(
    session: AsyncSession,
    email: str,
    user: User,
) -> None:
    login_token_value = "ABC123"  # noqa: S105
    conflicting_refresh_token_value = "existing-refresh-token"  # noqa: S105
    new_user_email = f"new_{email}"
    login_token = LoginToken(
        email=new_user_email,
        token_hash=hashlib.sha256(login_token_value.encode()).hexdigest(),
        expires_at=datetime.now(tz=UTC) + timedelta(minutes=10),
    )
    conflicting_refresh_token = RefreshToken(
        user_id=user.id,
        token_hash=hashlib.sha256(conflicting_refresh_token_value.encode()).hexdigest(),
        expires_at=datetime.now(tz=UTC) + timedelta(days=1),
    )
    session.add_all([login_token, conflicting_refresh_token])
    await session.commit()

    with (
        mock.patch.object(
            refresh_token_service.secrets,
            "token_urlsafe",
            mock.Mock(return_value=conflicting_refresh_token_value),
        ),
        pytest.raises(RefreshTokenGenerationError),
    ):
        await login_token_service.authenticate_with_login_token(session, login_token_value)

    # Verify that the login token and refresh token states are as expected after the failed authentication attempt.
    async with session.begin():
        await session.refresh(login_token)
        saved_user = await user_database.get_user_by_email(session, new_user_email)
        assert login_token.used_at is None
        assert saved_user is None
        result = await session.execute(select(RefreshToken))
        assert result.scalars().all() == [conflicting_refresh_token]

    # Authenticate with the login token again to ensure that a new refresh token can be generated.
    user, refresh_token_value = await login_token_service.authenticate_with_login_token(session, login_token_value)

    async with session.begin():
        await session.refresh(login_token)
        result = await session.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == hashlib.sha256(refresh_token_value.encode()).hexdigest(),
            ),
        )
        refresh_token = result.scalar_one()
        assert login_token.used_at is not None
        assert user.email == new_user_email
        assert refresh_token.user_id == user.id
