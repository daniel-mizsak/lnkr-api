"""
Tests for authentication dependencies.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest import mock

import jwt
import pytest
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from lnkr.api.dependencies import auth
from lnkr.config.application_settings import ApplicationEnvironment, application_settings
from lnkr.exceptions import UserDoesNotExistError
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
        assert await auth.get_current_user(None, session) is user
    get_user_by_email.assert_awaited_once_with(session, application_settings.DEVELOPMENT_USER_EMAIL)


async def test_get_current_user__production_without_credentials_is_forbidden() -> None:
    with (
        mock.patch.object(application_settings, "ENVIRONMENT", ApplicationEnvironment.PRODUCTION),
        pytest.raises(HTTPException) as exc_info,
    ):
        await auth.get_current_user(None, mock.AsyncMock())

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


async def test_get_current_user__empty_token_is_unauthorized() -> None:
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="")

    with pytest.raises(HTTPException) as exc_info:
        await auth.get_current_user(credentials, mock.AsyncMock())

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail == "Authorization token is missing"


async def test_get_current_user__invalid_token_is_unauthorized() -> None:
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid")

    with (
        mock.patch.object(auth, "decode_access_token", mock.Mock(side_effect=jwt.InvalidTokenError())),
        pytest.raises(HTTPException) as exc_info,
    ):
        await auth.get_current_user(credentials, mock.AsyncMock())

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail == "Invalid token"


async def test_get_current_user__invalid_subject_is_unauthorized() -> None:
    now = datetime.now(tz=UTC)
    payload = AccessTokenPayload(sub="not-a-uuid", iat=now, exp=now + timedelta(minutes=1), type="access")
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")

    with (
        mock.patch.object(auth, "decode_access_token", mock.Mock(return_value=payload)),
        pytest.raises(HTTPException) as exc_info,
    ):
        await auth.get_current_user(credentials, mock.AsyncMock())

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


async def test_get_current_user__loads_token_user(user: User) -> None:
    session = mock.AsyncMock()
    now = datetime.now(tz=UTC)
    payload = AccessTokenPayload(sub=str(user.id), iat=now, exp=now + timedelta(minutes=1), type="access")
    get_user_by_id = mock.AsyncMock(return_value=user)
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")

    with (
        mock.patch.object(auth, "decode_access_token", mock.Mock(return_value=payload)),
        mock.patch.object(auth, "get_user_by_id", get_user_by_id),
    ):
        assert await auth.get_current_user(credentials, session) is user
    get_user_by_id.assert_awaited_once_with(session, user.id)


async def test_get_current_user__missing_token_user_maps_domain_error(user_id: uuid.UUID) -> None:
    now = datetime.now(tz=UTC)
    payload = AccessTokenPayload(sub=str(user_id), iat=now, exp=now + timedelta(minutes=1), type="access")
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")

    with (
        mock.patch.object(auth, "decode_access_token", mock.Mock(return_value=payload)),
        mock.patch.object(
            auth,
            "get_user_by_id",
            mock.AsyncMock(side_effect=UserDoesNotExistError.by_id(user_id)),
        ),
        pytest.raises(HTTPException) as exc_info,
    ):
        await auth.get_current_user(credentials, mock.AsyncMock())

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc_info.value.detail[0]["type"] == "user_does_not_exist"  # ty: ignore[invalid-argument-type]
