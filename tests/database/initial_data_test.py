"""
Tests for initial database data creation.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING
from unittest import mock

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from lnkr.config.application_settings import ApplicationEnvironment, application_settings
from lnkr.database import initial_data
from lnkr.models import Click, Link, User

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def test_create_initial_data__production_does_not_open_session() -> None:
    with (
        mock.patch.object(application_settings, "ENVIRONMENT", ApplicationEnvironment.PRODUCTION),
        mock.patch.object(initial_data, "AsyncSessionLocal") as session_factory,
    ):
        await initial_data.create_initial_data()

    session_factory.begin.assert_not_called()
    session_factory.assert_not_called()


async def test_create_initial_data__development_creates_user_links_and_clicks(session: AsyncSession) -> None:
    email = "development@example.com"
    with (
        mock.patch.object(application_settings, "ENVIRONMENT", ApplicationEnvironment.DEVELOPMENT),
        mock.patch.object(application_settings, "DEVELOPMENT_USER_EMAIL", email),
        mock.patch.object(initial_data, "AsyncSessionLocal", async_sessionmaker(session.bind, expire_on_commit=False)),
    ):
        await initial_data.create_initial_data()

    user = await session.scalar(select(User).where(User.email == email))
    assert user is not None
    assert await session.scalar(select(Link).where(Link.user_id == user.id)) is not None
    assert await session.scalar(select(Click).join(Link).where(Link.user_id == user.id)) is not None
