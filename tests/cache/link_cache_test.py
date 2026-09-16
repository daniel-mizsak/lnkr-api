"""
Tests for the link cache.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING

from lnkr.cache.link_cache import (
    add_cached_link,
    get_cached_link_by_slug,
    set_cached_link_invalidated,
    set_cached_links_invalidated,
)
from lnkr.config.application_settings import application_settings

if TYPE_CHECKING:
    from redis.asyncio import Redis

    from lnkr.models import LinkCache


async def test_get_cached_link_by_slug__malformed_cached_link(cache: Redis, slug: str) -> None:
    await cache.set(f"link:{slug}", '{"slug": "slug"}')

    cached_link = await get_cached_link_by_slug(cache, slug)

    assert cached_link is None
    assert await cache.get(f"link:{slug}") is None


async def test_add_cached_link__configured_ttl_applied(cache: Redis, cached_link: LinkCache) -> None:
    await add_cached_link(cache, cached_link)

    ttl = await cache.ttl(f"link:{cached_link.slug}")
    expected_ttl = application_settings.LINK_CACHE_TTL_SECONDS
    assert expected_ttl - 1 <= ttl <= expected_ttl


async def test_add_cached_link__existing_entry_not_overwritten(cache: Redis, cached_link: LinkCache) -> None:
    updated_cached_link = cached_link.model_copy(update={"target_url": f"{cached_link.target_url}/updated"})
    await add_cached_link(cache, cached_link)

    await add_cached_link(cache, updated_cached_link)

    assert await get_cached_link_by_slug(cache, cached_link.slug) == cached_link


async def test_set_cached_link_invalidated__cached_link_treated_as_miss(cache: Redis, cached_link: LinkCache) -> None:
    await add_cached_link(cache, cached_link)

    await set_cached_link_invalidated(cache, cached_link.slug)
    await add_cached_link(cache, cached_link)

    assert await get_cached_link_by_slug(cache, cached_link.slug) is None
    ttl = await cache.ttl(f"link:{cached_link.slug}")
    assert 4 <= ttl <= 5


async def test_set_cached_links_invalidated__all_cached_links_treated_as_misses(
    cache: Redis, cached_link: LinkCache
) -> None:
    links = [cached_link.model_copy(update={"slug": f"slug-{index}"}) for index in range(10)]
    for link in links:
        await add_cached_link(cache, link)

    await set_cached_links_invalidated(cache, [link.slug for link in links])
    for link in links:
        await add_cached_link(cache, link)

        assert await get_cached_link_by_slug(cache, link.slug) is None
        ttl = await cache.ttl(f"link:{link.slug}")
        assert 4 <= ttl <= 5


async def test_set_cached_links_invalidated__unrelated_links_preserved(cache: Redis, cached_link: LinkCache) -> None:
    other_link = cached_link.model_copy(update={"slug": "other-slug"})
    await add_cached_link(cache, cached_link)
    await add_cached_link(cache, other_link)

    await set_cached_links_invalidated(cache, [other_link.slug])

    assert await get_cached_link_by_slug(cache, cached_link.slug) == cached_link


async def test_set_cached_links_invalidated__empty_list(cache: Redis, cached_link: LinkCache) -> None:
    await add_cached_link(cache, cached_link)
    await set_cached_links_invalidated(cache, [])
    assert await get_cached_link_by_slug(cache, cached_link.slug) == cached_link
