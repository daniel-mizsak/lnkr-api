"""
FastAPI dependency that provides the user authentication.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

from typing import TYPE_CHECKING, Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from lnkr.api.dependencies.database import get_session
from lnkr.config import Environment, settings
from lnkr.models import User, UserCreate
from lnkr.services.access_token_service import decode_access_token
from lnkr.services.user_service import get_or_create_user, get_user

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    """Authenticate and load user from the database."""
    if credentials is None:
        if settings.ENVIRONMENT == Environment.DEVELOPMENT:
            return await get_user(session, settings.DEVELOPMENT_USER_EMAIL)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authenticated")

    token = credentials.credentials
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization token is missing")

    try:
        access_token_payload = decode_access_token(token)
    except jwt.InvalidTokenError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from error

    # TODO: The user is re-created if it was deleted, but the token is still valid.
    return await get_or_create_user(session, UserCreate(email=access_token_payload.sub))
