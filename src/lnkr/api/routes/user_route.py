"""
API endpoints for managing users.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, Response, status

from lnkr.api.dependencies import get_cache, get_current_user, get_session
from lnkr.config.application_settings import application_settings
from lnkr.exceptions import UserDoesNotExistError
from lnkr.models import User, UserRead
from lnkr.services.user_service import delete_user

if TYPE_CHECKING:
    from redis.asyncio import Redis
    from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix=application_settings.USER_PREFIX)


@router.get("")
async def get_user_endpoint(user: Annotated[User, Depends(get_current_user)]) -> UserRead:
    """Get a user."""
    return UserRead.from_user(user)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_endpoint(
    session: Annotated[AsyncSession, Depends(get_session)],
    cache: Annotated[Redis, Depends(get_cache)],
    user: Annotated[User, Depends(get_current_user)],
) -> Response:
    """Delete user."""
    try:
        await delete_user(session, cache, user)
    except UserDoesNotExistError as user_does_not_exist_error:
        user_does_not_exist_error.raise_http_exception()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
