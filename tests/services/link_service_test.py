"""
Tests for the link service.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest import mock

import pytest
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
from lnkr.models import Link, LinkCache, LinkCreate, LinkStatus, User
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

    generate_slug = mock.Mock(side_effect=[link.slug, slug_other])
    with mock.patch.object(link_service, "_generate_random_slug", generate_slug):
        assert await link_service.generate_unused_random_slug(session) == slug_other

    assert generate_slug.call_args_list == [mock.call(6), mock.call(7)]


async def test_generate_unused_random_slug__exhaustion_raises_domain_error(session: AsyncSession, link: Link) -> None:
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
        assert await link_service.get_cached_link(mock.AsyncMock(), mock.AsyncMock(), cached_link.slug) is cached_link

    get_link.assert_not_awaited()


async def test_get_cached_link__cache_miss_loads_database_and_populates_cache(
    session: AsyncSession, link: Link
) -> None:
    session.add(link)
    await session.commit()

    cache = mock.AsyncMock()
    get_cached_link = mock.AsyncMock(return_value=None)
    add_cached_link = mock.AsyncMock()
    with (
        mock.patch.object(link_service.link_cache, "get_cached_link_by_slug", get_cached_link),
        mock.patch.object(link_service.link_cache, "add_cached_link", add_cached_link),
    ):
        result = await link_service.get_cached_link(session, cache, link.slug)

    assert result == LinkCache.from_link(link)
    add_cached_link.assert_awaited_once_with(cache, result)


async def test_get_cached_link__cache_read_failure_treated_as_miss(session: AsyncSession, link: Link) -> None:
    session.add(link)
    await session.commit()

    cache = mock.AsyncMock()
    get_cached_link = mock.AsyncMock(side_effect=RedisError())
    add_cached_link = mock.AsyncMock()
    with (
        mock.patch.object(link_service.link_cache, "get_cached_link_by_slug", get_cached_link),
        mock.patch.object(link_service.link_cache, "add_cached_link", add_cached_link),
    ):
        result = await link_service.get_cached_link(session, cache, link.slug)

    assert result == LinkCache.from_link(link)
    add_cached_link.assert_awaited_once_with(cache, result)


async def test_get_cached_link__disabled_link_raises_domain_error(cached_link: LinkCache) -> None:
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


async def test_get_cached_link__expired_link_raises_domain_error(cached_link: LinkCache) -> None:
    expired_link = cached_link.model_copy(
        update={"expires_at": datetime.now(tz=UTC) - timedelta(seconds=1)},
    )
    with (
        mock.patch.object(
            link_service.link_cache,
            "get_cached_link_by_slug",
            mock.AsyncMock(return_value=expired_link),
        ),
        pytest.raises(LinkExpiredError),
    ):
        await link_service.get_cached_link(mock.AsyncMock(), mock.AsyncMock(), expired_link.slug)


async def test_get_cached_link_validate_password__rejects_invalid_password(cached_link: LinkCache) -> None:
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


async def test_get_link_validate_user__ownership_validated(
    session: AsyncSession,
    link: Link,
    user: User,
    user_other: User,
) -> None:
    session.add(link)
    await session.commit()

    assert await link_service.get_link_validate_user(session, link.slug, user) is link

    with pytest.raises(SlugNotOwnedByUserError):
        await link_service.get_link_validate_user(session, link.slug, user_other)


async def test_get_link_validate_user__slug_does_not_exist(
    session: AsyncSession,
    user: User,
    slug: str,
) -> None:
    with pytest.raises(SlugDoesNotExistError):
        await link_service.get_link_validate_user(session, slug, user)


async def test_delete_link__cache_failure_ignored(
    session: AsyncSession,
    link: Link,
    user: User,
) -> None:
    session.add(link)
    await session.commit()

    cache = mock.AsyncMock()
    with mock.patch.object(
        link_service.link_cache,
        "delete_cached_link_by_slug",
        mock.AsyncMock(side_effect=RedisError()),
    ):
        await link_service.delete_link(session, cache, link.slug, user)

    assert await link_service.link_database.get_link_by_slug(session, link.slug) is None


async def test_list_links__normalizes_search_and_caps_page_size(user: User) -> None:
    session = mock.AsyncMock()
    list_links_by_user = mock.AsyncMock(return_value=([], 0))
    favorites_only = False
    with mock.patch.object(link_service.link_database, "list_links_by_user", list_links_by_user):
        assert await link_service.list_links(
            session,
            user,
            "  search  ",
            favorites_only,
            "updated_at",
            "descending",
            500,
            2,
        ) == ([], 0)

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


async def test_list_links__blank_search_treated_as_unfiltered(
    session: AsyncSession,
    user: User,
    link: Link,
) -> None:
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
