"""
Tests for the user service.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest import mock

import pytest
from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError

from lnkr.database.tokens import login_token_database
from lnkr.exceptions import UserDoesNotExistError
from lnkr.models import Link, LoginToken, User, UserCreate
from lnkr.services import user_service

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def test_get_user_by_id__user_does_not_exist(session: AsyncSession) -> None:
    unknown_user_id = uuid.uuid4()

    with pytest.raises(UserDoesNotExistError, match=str(unknown_user_id)):
        await user_service.get_user_by_id(session, unknown_user_id)


async def test_get_user_by_email__user_does_not_exist(session: AsyncSession, email: str) -> None:
    email_missing = f"missing_{email}"

    with pytest.raises(UserDoesNotExistError, match=email_missing):
        await user_service.get_user_by_email(session, email_missing)


async def test_get_or_create_user_without_commit__existing_user_returned(
    session: AsyncSession,
    email: str,
    user: User,
) -> None:
    user_create = UserCreate(email=email)

    async with session.begin():
        existing_user = await user_service.get_or_create_user_without_commit(session, user_create)

    assert existing_user.id == user.id
    assert existing_user.email == user.email


async def test_get_or_create_user_without_commit__new_user_created(session: AsyncSession, email: str) -> None:
    new_user_email = f"new_{email}"

    async with session.begin():
        created_user = await user_service.get_or_create_user_without_commit(session, UserCreate(email=new_user_email))

    saved_user = await user_service.get_user_by_email(session, new_user_email)

    assert saved_user.id == created_user.id
    assert saved_user.email == new_user_email


async def test_get_or_create_user_without_commit__conflict_preserves_outer_transaction(
    session: AsyncSession,
    email: str,
    user: User,
) -> None:
    login_token = LoginToken(
        email=email,
        token_hash="a" * 64,
        expires_at=datetime.now(tz=UTC) + timedelta(minutes=10),
    )
    session.add(login_token)
    await session.commit()

    # Simulate a user appearing after the first lookup.
    get_user_by_email = mock.AsyncMock(
        wraps=user_service.user_database.get_user_by_email,
        side_effect=[None, mock.DEFAULT],
    )
    async with session.begin():
        await login_token_database.consume_login_token(session, login_token.token_hash)
        with mock.patch.object(user_service.user_database, "get_user_by_email", get_user_by_email):
            existing_user = await user_service.get_or_create_user_without_commit(session, UserCreate(email=email))

    assert get_user_by_email.await_args_list == [mock.call(session, email), mock.call(session, email)]
    assert existing_user.id == user.id
    assert existing_user.email == email
    await session.refresh(login_token)
    assert login_token.used_at is not None


async def test_delete_user__user_does_not_exist(session: AsyncSession, user: User) -> None:
    user_id = user.id
    await session.delete(user)
    await session.commit()
    with (
        mock.patch.object(user_service.link_cache, "set_cached_links_invalidated") as set_cached_links_invalidated,
        pytest.raises(UserDoesNotExistError, match=str(user_id)),
    ):
        await user_service.delete_user(session, mock.AsyncMock(), user)

    assert not session.in_transaction()
    set_cached_links_invalidated.assert_not_awaited()


async def test_delete_user__deletion_failure_rolls_back_without_invalidating_cache(
    session: AsyncSession,
    user: User,
    link: Link,
) -> None:
    user_id = user.id
    link_id = link.id
    login_token = LoginToken(
        email=user.email,
        token_hash="a" * 64,
        expires_at=datetime.now(tz=UTC) + timedelta(minutes=10),
    )
    session.add_all([link, login_token])
    await session.commit()

    login_token_id = login_token.id
    cache = mock.AsyncMock()
    with (
        mock.patch.object(
            user_service.user_database, "delete_user", mock.AsyncMock(side_effect=SQLAlchemyError("database failure"))
        ),
        mock.patch.object(user_service.link_cache, "set_cached_links_invalidated") as set_cached_links_invalidated,
        pytest.raises(SQLAlchemyError, match="database failure"),
    ):
        await user_service.delete_user(session, cache, user)

    set_cached_links_invalidated.assert_not_awaited()
    assert not session.in_transaction()
    assert await session.get(User, user_id) is not None
    assert await session.get(Link, link_id) is not None
    assert await session.get(LoginToken, login_token_id) is not None


async def test_delete_user__commit_failure_rolls_back_without_invalidating_cache(
    session: AsyncSession,
    user: User,
    link: Link,
) -> None:
    user_id = user.id
    link_id = link.id
    login_token = LoginToken(
        email=user.email,
        token_hash="a" * 64,
        expires_at=datetime.now(tz=UTC) + timedelta(minutes=10),
    )
    session.add_all([link, login_token])
    await session.commit()

    login_token_id = login_token.id
    cache = mock.AsyncMock()
    with (
        mock.patch.object(session, "commit", mock.AsyncMock(side_effect=SQLAlchemyError("database failure"))),
        mock.patch.object(user_service.link_cache, "set_cached_links_invalidated") as set_cached_links_invalidated,
        pytest.raises(SQLAlchemyError, match="database failure"),
    ):
        await user_service.delete_user(session, cache, user)

    set_cached_links_invalidated.assert_not_awaited()
    assert not session.in_transaction()
    assert await session.get(User, user_id) is not None
    assert await session.get(Link, link_id) is not None
    assert await session.get(LoginToken, login_token_id) is not None


async def test_delete_user__cache_failure_ignored(session: AsyncSession, user: User, link: Link) -> None:
    user_id = user.id
    slug = link.slug
    session.add(link)
    await session.commit()

    cache = mock.AsyncMock()
    set_cached_links_invalidated = mock.AsyncMock(side_effect=RedisError("cache failure"))
    with mock.patch.object(user_service.link_cache, "set_cached_links_invalidated", set_cached_links_invalidated):
        await user_service.delete_user(session, cache, user)

    set_cached_links_invalidated.assert_awaited_once_with(cache, [slug])
    assert await session.get(User, user_id) is None
    assert await user_service.link_database.get_link_by_slug(session, slug) is None
