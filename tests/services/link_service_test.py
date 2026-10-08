"""
Tests for the link service.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest import mock

import pytest
import time_machine
from redis.exceptions import RedisError

from lnkr.config.application_settings import application_settings
from lnkr.exceptions import (
    LinkDisabledError,
    LinkExpiredError,
    LinkPasswordInvalidError,
    RandomSlugGenerationError,
    SlugAlreadyExistsError,
    SlugDoesNotExistError,
    SlugNotOwnedByUserError,
    UserDoesNotExistError,
    UserLinkLimitExceededError,
)
from lnkr.models import Link, LinkCache, LinkCreate, LinkStatus, LinkUpdate, User
from lnkr.services import link_service

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture(name="link_create")
def link_create_fixture(slug: str, target_url: str) -> LinkCreate:
    return LinkCreate.model_validate({"slug": slug, "target_url": target_url})


async def test_create_link__defaults_applied(
    session: AsyncSession,
    user: User,
    link_create: LinkCreate,
) -> None:
    link = await link_service.create_link(session, link_create, user)

    assert link.status == LinkStatus.ACTIVE
    assert link.favorite is False
    assert link.expires_at is None
    assert link.password_hash is None


async def test_create_link__user_does_not_exist(
    session: AsyncSession,
    link_create: LinkCreate,
    email: str,
) -> None:
    user_missing = User(id=uuid.uuid4(), email=f"missing_{email}")

    with pytest.raises(UserDoesNotExistError):
        await link_service.create_link(session, link_create, user_missing)


async def test_create_link__user_link_limit_exceeded(
    session: AsyncSession,
    user: User,
    link: Link,
    slug_other: str,
    target_url: str,
) -> None:
    session.add(link)
    await session.commit()
    link_create = LinkCreate.model_validate({"slug": slug_other, "target_url": target_url})

    with (
        mock.patch.object(application_settings, "USER_LINK_LIMIT", 1),
        pytest.raises(UserLinkLimitExceededError),
    ):
        await link_service.create_link(session, link_create, user)


async def test_create_link__slug_already_exists(
    session: AsyncSession,
    user: User,
    link: Link,
    link_create: LinkCreate,
) -> None:
    session.add(link)
    await session.commit()

    with pytest.raises(SlugAlreadyExistsError):
        await link_service.create_link(session, link_create, user)


async def test_generate_unused_random_slug__retries_with_increasing_length(
    session: AsyncSession,
    link: Link,
    slug_other: str,
) -> None:
    session.add(link)
    await session.commit()

    generate_random_slug = mock.Mock(side_effect=[link.slug, slug_other])

    with mock.patch.object(link_service, "_generate_random_slug", generate_random_slug):
        generated_slug = await link_service.generate_unused_random_slug(session)

    assert generated_slug == slug_other
    assert generate_random_slug.call_args_list == [mock.call(6), mock.call(7)]


async def test_generate_unused_random_slug__generation_attempts_exhausted(session: AsyncSession, link: Link) -> None:
    session.add(link)
    await session.commit()

    with (
        mock.patch.object(link_service, "_generate_random_slug", mock.Mock(return_value=link.slug)),
        pytest.raises(RandomSlugGenerationError),
    ):
        await link_service.generate_unused_random_slug(session)


async def test_get_cached_link__cache_hit_avoids_database(cached_link: LinkCache) -> None:
    get_link = mock.AsyncMock()

    with (
        mock.patch.object(
            link_service.link_cache,
            "get_cached_link_by_slug",
            mock.AsyncMock(return_value=cached_link),
        ),
        mock.patch.object(link_service, "_get_link", get_link),
    ):
        retrieved_link = await link_service.get_cached_link(mock.AsyncMock(), mock.AsyncMock(), cached_link.slug)

    assert retrieved_link is cached_link
    get_link.assert_not_awaited()


async def test_get_cached_link__cache_miss_loads_database_and_populates_cache(
    session: AsyncSession,
    link: Link,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger=link_service.__name__)
    session.add(link)
    await session.commit()

    cache = mock.AsyncMock()
    get_cached_link_by_slug = mock.AsyncMock(return_value=None)
    add_cached_link = mock.AsyncMock()

    with (
        mock.patch.object(link_service.link_cache, "get_cached_link_by_slug", get_cached_link_by_slug),
        mock.patch.object(link_service.link_cache, "add_cached_link", add_cached_link),
    ):
        retrieved_link = await link_service.get_cached_link(session, cache, link.slug)

    assert retrieved_link == LinkCache.from_link(link)
    add_cached_link.assert_awaited_once_with(cache, retrieved_link)
    assert caplog.record_tuples == []


async def test_get_cached_link__cache_read_failure_loads_database_and_populates_cache(
    session: AsyncSession,
    link: Link,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger=link_service.__name__)
    session.add(link)
    await session.commit()

    cache_error = RedisError("cache failure")
    cache = mock.AsyncMock()
    get_cached_link_by_slug = mock.AsyncMock(side_effect=cache_error)
    add_cached_link = mock.AsyncMock()

    with (
        mock.patch.object(link_service.link_cache, "get_cached_link_by_slug", get_cached_link_by_slug),
        mock.patch.object(link_service.link_cache, "add_cached_link", add_cached_link),
    ):
        retrieved_link = await link_service.get_cached_link(session, cache, link.slug)

    assert retrieved_link == LinkCache.from_link(link)
    add_cached_link.assert_awaited_once_with(cache, retrieved_link)
    assert caplog.record_tuples == [(link_service.__name__, logging.WARNING, "redis.get_cached_link_failed")]
    assert caplog.records[0].exc_info is not None
    assert caplog.records[0].exc_info[1] is cache_error


async def test_get_cached_link__cache_write_failure_ignored(
    session: AsyncSession,
    link: Link,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger=link_service.__name__)
    session.add(link)
    await session.commit()

    cache_error = RedisError("cache write failure")
    cache = mock.AsyncMock()

    with (
        mock.patch.object(link_service.link_cache, "get_cached_link_by_slug", mock.AsyncMock(return_value=None)),
        mock.patch.object(link_service.link_cache, "add_cached_link", mock.AsyncMock(side_effect=cache_error)),
    ):
        retrieved_link = await link_service.get_cached_link(session, cache, link.slug)

    assert retrieved_link == LinkCache.from_link(link)
    assert caplog.record_tuples == [(link_service.__name__, logging.WARNING, "redis.add_cached_link_failed")]
    assert caplog.records[0].exc_info is not None
    assert caplog.records[0].exc_info[1] is cache_error


async def test_get_cached_link__disabled_link(cached_link: LinkCache) -> None:
    disabled_link = cached_link.model_copy(update={"status": LinkStatus.DISABLED})

    with (
        mock.patch.object(
            link_service.link_cache,
            "get_cached_link_by_slug",
            mock.AsyncMock(return_value=disabled_link),
        ),
        pytest.raises(LinkDisabledError),
    ):
        await link_service.get_cached_link(mock.AsyncMock(), mock.AsyncMock(), disabled_link.slug)


@pytest.mark.parametrize(
    "elapsed",
    [pytest.param(timedelta(0), id="at-expiration"), pytest.param(timedelta(microseconds=1), id="after-expiration")],
)
async def test_get_cached_link__expired_link(cached_link: LinkCache, elapsed: timedelta) -> None:
    expires_at = datetime(2026, 1, 1, tzinfo=UTC)
    expired_link = cached_link.model_copy(update={"expires_at": expires_at})

    with (
        time_machine.travel(expires_at + elapsed, tick=False),
        mock.patch.object(
            link_service.link_cache, "get_cached_link_by_slug", mock.AsyncMock(return_value=expired_link)
        ),
        pytest.raises(LinkExpiredError),
    ):
        await link_service.get_cached_link(mock.AsyncMock(), mock.AsyncMock(), expired_link.slug)


async def test_get_cached_link__immediately_before_expiration(cached_link: LinkCache) -> None:
    expires_at = datetime(2026, 1, 1, tzinfo=UTC)
    expiring_link = cached_link.model_copy(update={"expires_at": expires_at})

    with (
        time_machine.travel(expires_at - timedelta(microseconds=1), tick=False),
        mock.patch.object(
            link_service.link_cache, "get_cached_link_by_slug", mock.AsyncMock(return_value=expiring_link)
        ),
    ):
        retrieved_link = await link_service.get_cached_link(mock.AsyncMock(), mock.AsyncMock(), expiring_link.slug)

    assert retrieved_link is expiring_link


async def test_get_cached_link_validate_password__invalid_password(cached_link: LinkCache) -> None:
    protected_link = cached_link.model_copy(update={"password_hash": "hash"})

    with (
        mock.patch.object(link_service, "get_cached_link", mock.AsyncMock(return_value=protected_link)),
        mock.patch.object(link_service, "_verify_password", mock.AsyncMock(return_value=False)),
        pytest.raises(LinkPasswordInvalidError),
    ):
        await link_service.get_cached_link_validate_password(
            mock.AsyncMock(),
            mock.AsyncMock(),
            protected_link.slug,
            "wrong",
        )


async def test_get_link_validate_user__slug_owned_by_current_user(
    session: AsyncSession,
    link: Link,
    user: User,
) -> None:
    session.add(link)
    await session.commit()

    owned_link = await link_service.get_link_validate_user(session, link.slug, user)

    assert owned_link is link


async def test_get_link_validate_user__slug_not_owned_by_user(
    session: AsyncSession,
    link: Link,
    user_other: User,
) -> None:
    session.add(link)
    await session.commit()

    with pytest.raises(SlugNotOwnedByUserError):
        await link_service.get_link_validate_user(session, link.slug, user_other)


async def test_get_link_validate_user__slug_does_not_exist(
    session: AsyncSession,
    user: User,
    slug: str,
    link_other: Link,
) -> None:
    session.add(link_other)
    await session.commit()

    with pytest.raises(SlugDoesNotExistError):
        await link_service.get_link_validate_user(session, slug, user)


async def test_update_link__cache_invalidated(
    session: AsyncSession,
    link: Link,
    user: User,
    target_url: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger=link_service.__name__)
    session.add(link)
    await session.commit()

    cache = mock.AsyncMock()
    set_cached_link_invalidated = mock.AsyncMock()
    link_update = LinkUpdate.model_validate({"target_url": f"{target_url}/updated"})

    with mock.patch.object(link_service.link_cache, "set_cached_link_invalidated", set_cached_link_invalidated):
        updated_link = await link_service.update_link(session, cache, link.slug, link_update, user)

    assert updated_link.target_url == f"{target_url}/updated"
    set_cached_link_invalidated.assert_awaited_once_with(cache, link.slug)
    assert caplog.record_tuples == []


async def test_update_link__cache_invalidation_failure_ignored(
    session: AsyncSession,
    link: Link,
    user: User,
    target_url: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger=link_service.__name__)
    session.add(link)
    await session.commit()

    cache_error = RedisError("cache failure")
    cache = mock.AsyncMock()
    set_cached_link_invalidated = mock.AsyncMock(side_effect=cache_error)
    link_update = LinkUpdate.model_validate({"target_url": f"{target_url}/updated"})

    with mock.patch.object(link_service.link_cache, "set_cached_link_invalidated", set_cached_link_invalidated):
        updated_link = await link_service.update_link(session, cache, link.slug, link_update, user)

    assert updated_link.target_url == f"{target_url}/updated"
    set_cached_link_invalidated.assert_awaited_once_with(cache, link.slug)
    assert caplog.record_tuples == [
        (link_service.__name__, logging.WARNING, "redis.set_cached_link_invalidation_failed")
    ]
    assert caplog.records[0].exc_info is not None
    assert caplog.records[0].exc_info[1] is cache_error


async def test_delete_link__cache_invalidated(
    session: AsyncSession,
    link: Link,
    user: User,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger=link_service.__name__)
    session.add(link)
    await session.commit()

    cache = mock.AsyncMock()
    set_cached_link_invalidated = mock.AsyncMock()

    with mock.patch.object(link_service.link_cache, "set_cached_link_invalidated", set_cached_link_invalidated):
        await link_service.delete_link(session, cache, link.slug, user)

    deleted_link = await link_service.link_database.get_link_by_slug(session, link.slug)

    assert deleted_link is None
    set_cached_link_invalidated.assert_awaited_once_with(cache, link.slug)
    assert caplog.record_tuples == []


async def test_delete_link__cache_invalidation_failure_ignored(
    session: AsyncSession,
    link: Link,
    user: User,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger=link_service.__name__)
    session.add(link)
    await session.commit()

    cache_error = RedisError("cache failure")
    cache = mock.AsyncMock()
    set_cached_link_invalidated = mock.AsyncMock(side_effect=cache_error)

    with mock.patch.object(link_service.link_cache, "set_cached_link_invalidated", set_cached_link_invalidated):
        await link_service.delete_link(session, cache, link.slug, user)

    deleted_link = await link_service.link_database.get_link_by_slug(session, link.slug)

    assert deleted_link is None
    set_cached_link_invalidated.assert_awaited_once_with(cache, link.slug)
    assert caplog.record_tuples == [
        (link_service.__name__, logging.WARNING, "redis.set_cached_link_invalidation_failed")
    ]
    assert caplog.records[0].exc_info is not None
    assert caplog.records[0].exc_info[1] is cache_error


async def test_list_links__normalizes_search_and_caps_page_size(user: User) -> None:
    session = mock.AsyncMock()
    list_links_by_user = mock.AsyncMock(return_value=([], 0))
    favorites_only = False

    with mock.patch.object(link_service.link_database, "list_links_by_user", list_links_by_user):
        links, total = await link_service.list_links(
            session,
            user,
            "  search  ",
            favorites_only,
            "updated_at",
            "descending",
            500,
            2,
        )

    assert links == []
    assert total == 0
    list_links_by_user.assert_awaited_once_with(
        session,
        user,
        "search",
        favorites_only,
        "updated_at",
        "descending",
        100,
        2,
    )


async def test_list_links__blank_search_treated_as_unfiltered(session: AsyncSession, user: User, link: Link) -> None:
    session.add(link)
    await session.commit()
    favorites_only = False

    links, total = await link_service.list_links(
        session,
        user,
        "   ",
        favorites_only,
        "created_at",
        "ascending",
        10,
        1,
    )

    assert total == 1
    assert [listed_link.id for listed_link in links] == [link.id]
