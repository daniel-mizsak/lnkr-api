"""
Tests for the user service.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

import uuid
from typing import TYPE_CHECKING

import pytest

from lnkr.exceptions import UserDoesNotExistError
from lnkr.models import UserCreate
from lnkr.services import user_service

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from lnkr.models import User


async def test_get_user_by_id__user_does_not_exist(session: AsyncSession) -> None:
    unknown_user_id = uuid.uuid4()

    with pytest.raises(UserDoesNotExistError, match=str(unknown_user_id)):
        await user_service.get_user_by_id(session, unknown_user_id)


async def test_get_user_by_email__user_does_not_exist(session: AsyncSession, email: str) -> None:
    email_missing = f"missing_{email}"

    with pytest.raises(UserDoesNotExistError, match=email_missing):
        await user_service.get_user_by_email(session, email_missing)


async def test_get_or_create_user__existing_user_returned(session: AsyncSession, email: str, user: User) -> None:
    user_create = UserCreate(email=email)

    existing_user = await user_service.get_or_create_user(session, user_create)

    assert existing_user.id == user.id
    assert existing_user.email == user.email
