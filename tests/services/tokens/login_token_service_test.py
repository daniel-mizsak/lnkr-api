"""
Tests for the login token service.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

import hashlib
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest import mock

import pytest

from lnkr.exceptions import LoginTokenGenerationError
from lnkr.models import IpAddress, LoginToken, LoginTokenCreate, UserAgent
from lnkr.services.tokens import login_token_service

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


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
        mock.patch.object(
            login_token_service.secrets,
            "choice",
            mock.Mock(return_value=generated_character),
        ),
        pytest.raises(LoginTokenGenerationError),
    ):
        await login_token_service.create_and_save_login_token(
            session,
            LoginTokenCreate(email=email),
            IpAddress(),
            None,
            UserAgent(),
        )
