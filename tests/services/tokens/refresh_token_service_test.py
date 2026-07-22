"""
Tests for the refresh token service.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

import hashlib
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest import mock

import pytest

from lnkr.exceptions import RefreshTokenGenerationError, RefreshTokenInvalidError
from lnkr.models import RefreshToken
from lnkr.services.tokens import refresh_token_service

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from lnkr.models import User


async def test_create_and_save_refresh_token__generation_attempts_exhausted(session: AsyncSession, user: User) -> None:
    refresh_token_value = "refresh-token"  # noqa: S105
    session.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hashlib.sha256(refresh_token_value.encode()).hexdigest(),
            expires_at=datetime.now(tz=UTC) + timedelta(days=1),
        ),
    )
    await session.commit()

    with (
        mock.patch.object(
            refresh_token_service.secrets,
            "token_urlsafe",
            mock.Mock(return_value=refresh_token_value),
        ),
        pytest.raises(RefreshTokenGenerationError),
    ):
        await refresh_token_service.create_and_save_refresh_token(session, user.id)


async def test_rotate_refresh_token__replacement_failure_preserves_original_token(
    session: AsyncSession,
    user: User,
) -> None:
    refresh_token_value = "refresh-token"  # noqa: S105
    replacement_token_value = "replacement-refresh-token"  # noqa: S105
    refresh_token = RefreshToken(
        user_id=user.id,
        token_hash=hashlib.sha256(refresh_token_value.encode()).hexdigest(),
        expires_at=datetime.now(tz=UTC) + timedelta(days=1),
    )
    replacement_token = RefreshToken(
        user_id=user.id,
        token_hash=hashlib.sha256(replacement_token_value.encode()).hexdigest(),
        expires_at=datetime.now(tz=UTC) + timedelta(days=1),
    )
    session.add_all([refresh_token, replacement_token])
    await session.commit()

    with (
        mock.patch.object(
            refresh_token_service.secrets,
            "token_urlsafe",
            mock.Mock(return_value=replacement_token_value),
        ),
        pytest.raises(RefreshTokenGenerationError),
    ):
        await refresh_token_service.rotate_refresh_token(session, refresh_token_value)

    await session.refresh(refresh_token)
    assert refresh_token.used_at is None

    # The failed rotation must leave the original token consumable.
    await refresh_token_service.rotate_refresh_token(session, refresh_token_value)


async def test_rotate_refresh_token__original_consumed_and_replacement_consumable(
    session: AsyncSession,
    user: User,
) -> None:
    # Preserve the id because the expected rollback below expires ORM attributes.
    user_id = user.id
    original_token_value = await refresh_token_service.create_and_save_refresh_token(session, user_id)

    rotated_user_id, replacement_token_value = await refresh_token_service.rotate_refresh_token(
        session,
        original_token_value,
    )

    assert rotated_user_id == user_id
    assert replacement_token_value != original_token_value
    with pytest.raises(RefreshTokenInvalidError):
        await refresh_token_service.rotate_refresh_token(session, original_token_value)

    second_rotated_user_id, second_replacement_token_value = await refresh_token_service.rotate_refresh_token(
        session,
        replacement_token_value,
    )

    assert second_rotated_user_id == user_id
    assert second_replacement_token_value != replacement_token_value
