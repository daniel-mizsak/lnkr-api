"""
FastAPI dependency that provides the user authentication.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

import uuid
from typing import TYPE_CHECKING, Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from lnkr.api.dependencies.database import get_session
from lnkr.config.application_settings import ApplicationEnvironment, application_settings
from lnkr.exceptions import UserDoesNotExistError
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
            return await get_user_by_email(session, application_settings.DEVELOPMENT_USER_EMAIL)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authenticated")

    token = credentials.credentials
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization token is missing")

    try:
        access_token_payload = decode_access_token(token)
    except jwt.InvalidTokenError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from error

    try:
        user_id = uuid.UUID(access_token_payload.sub)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from error

    try:
        return await get_user_by_id(session, user_id)
    except UserDoesNotExistError as user_does_not_exist_error:
        user_does_not_exist_error.raise_http_exception()
