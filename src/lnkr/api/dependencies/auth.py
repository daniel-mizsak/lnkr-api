"""
FastAPI dependency that provides the user authentication.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

import uuid
from typing import TYPE_CHECKING, Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from lnkr.api.dependencies.database import get_session
from lnkr.config.application_settings import ApplicationEnvironment, application_settings
from lnkr.exceptions import (
    AccessCredentialsMissingError,
    AccessTokenInvalidError,
    AccessTokenMissingError,
    AccessTokenSubjectInvalidError,
    UserDoesNotExistError,
)
from lnkr.services.tokens.access_token_service import decode_access_token
from lnkr.services.user_service import get_user_by_email, get_user_by_id

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from lnkr.models import User

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    """Authenticate and load user from the database."""
    if credentials is None:
        if application_settings.ENVIRONMENT == ApplicationEnvironment.DEVELOPMENT:
            try:
                return await get_user_by_email(session, application_settings.DEVELOPMENT_USER_EMAIL)
            except UserDoesNotExistError as user_does_not_exist_error:
                # A missing configured development account is a server failure, not a client rejection.
                message = "Configured development user does not exist"
                raise RuntimeError(message) from user_does_not_exist_error
        raise AccessCredentialsMissingError

    token = credentials.credentials
    if not token:
        raise AccessTokenMissingError

    try:
        access_token_payload = decode_access_token(token)
    except jwt.InvalidTokenError as invalid_token_error:
        raise AccessTokenInvalidError from invalid_token_error

    try:
        user_id = uuid.UUID(access_token_payload.sub)
    except ValueError as value_error:
        raise AccessTokenSubjectInvalidError from value_error

    return await get_user_by_id(session, user_id)
