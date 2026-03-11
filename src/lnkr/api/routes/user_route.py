"""
API endpoints for managing users.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from lnkr.api.dependencies import get_current_user
from lnkr.config import settings
from lnkr.models import User, UserRead

router = APIRouter(prefix=settings.USER_PREFIX)


@router.get("")
async def get_user_endpoint(user: Annotated[User, Depends(get_current_user)]) -> UserRead:
    """Get a user."""
    return UserRead.from_user(user)
