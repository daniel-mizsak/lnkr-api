"""
API endpoints for managing users.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from lnkr.api.dependencies import get_current_user
from lnkr.config.application_settings import application_settings
from lnkr.models import User, UserRead

router = APIRouter(prefix=application_settings.USER_PREFIX)


@router.get("")
async def get_user_endpoint(user: Annotated[User, Depends(get_current_user)]) -> UserRead:
    """Get a user."""
    return UserRead.from_user(user)
