"""
Tests for authentication dependencies.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from unittest import mock

import jwt
import pytest
from fastapi.security import HTTPAuthorizationCredentials

from lnkr.api.dependencies import auth
from lnkr.config.application_settings import ApplicationEnvironment, application_settings
from lnkr.exceptions import (
    AccessCredentialsMissingError,
    AccessTokenInvalidError,
    AccessTokenMissingError,
    AccessTokenSubjectInvalidError,
    UserDoesNotExistError,
)
from lnkr.models import AccessTokenPayload, User

if TYPE_CHECKING:
    import uuid


async def test_get_current_user__development_without_credentials_uses_configured_user(user: User) -> None:
    session = mock.AsyncMock()
    get_user_by_email = mock.AsyncMock(return_value=user)

    with (
        mock.patch.object(application_settings, "ENVIRONMENT", ApplicationEnvironment.DEVELOPMENT),
        mock.patch.object(auth, "get_user_by_email", get_user_by_email),
    ):
        current_user = await auth.get_current_user(None, session)

    assert current_user is user
    get_user_by_email.assert_awaited_once_with(session, application_settings.DEVELOPMENT_USER_EMAIL)


async def test_get_current_user__production_without_credentials_is_forbidden() -> None:
    with (
        mock.patch.object(application_settings, "ENVIRONMENT", ApplicationEnvironment.PRODUCTION),
        pytest.raises(AccessCredentialsMissingError),
    ):
        await auth.get_current_user(None, mock.AsyncMock())


async def test_get_current_user__empty_token_is_unauthorized() -> None:
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="")

    with pytest.raises(AccessTokenMissingError) as exc_info:
        await auth.get_current_user(credentials, mock.AsyncMock())

    assert str(exc_info.value) == "Authorization token is missing"


async def test_get_current_user__invalid_token_is_unauthorized() -> None:
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid")

    with (
        mock.patch.object(auth, "decode_access_token", mock.Mock(side_effect=jwt.InvalidTokenError())),
        pytest.raises(AccessTokenInvalidError) as exc_info,
    ):
        await auth.get_current_user(credentials, mock.AsyncMock())

    assert str(exc_info.value) == "Invalid token"


async def test_get_current_user__invalid_subject_is_unauthorized(now: datetime) -> None:
    payload = AccessTokenPayload(sub="not-a-uuid", iat=now, exp=now + timedelta(minutes=1), type="access")
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")

    with (
        mock.patch.object(auth, "decode_access_token", mock.Mock(return_value=payload)),
        pytest.raises(AccessTokenSubjectInvalidError),
    ):
        await auth.get_current_user(credentials, mock.AsyncMock())


async def test_get_current_user__missing_token_user_raises_domain_error(user_id: uuid.UUID, now: datetime) -> None:
    payload = AccessTokenPayload(sub=str(user_id), iat=now, exp=now + timedelta(minutes=1), type="access")
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")

    with (
        mock.patch.object(auth, "decode_access_token", mock.Mock(return_value=payload)),
        mock.patch.object(
            auth,
            "get_user_by_id",
            mock.AsyncMock(side_effect=UserDoesNotExistError.by_id(user_id)),
        ),
        pytest.raises(UserDoesNotExistError) as exc_info,
    ):
        await auth.get_current_user(credentials, mock.AsyncMock())

    assert str(exc_info.value) == f"User with id '{user_id}' does not exist"


async def test_get_current_user__loads_token_user(user: User, now: datetime) -> None:
    session = mock.AsyncMock()
    payload = AccessTokenPayload(sub=str(user.id), iat=now, exp=now + timedelta(minutes=1), type="access")
    get_user_by_id = mock.AsyncMock(return_value=user)
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")

    with (
        mock.patch.object(auth, "decode_access_token", mock.Mock(return_value=payload)),
        mock.patch.object(auth, "get_user_by_id", get_user_by_id),
    ):
        current_user = await auth.get_current_user(credentials, session)

    assert current_user is user
    get_user_by_id.assert_awaited_once_with(session, user.id)
