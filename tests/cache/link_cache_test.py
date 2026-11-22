"""
Tests for the link cache.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

import logging
from typing import TYPE_CHECKING
from unittest import mock

from lnkr.cache.link_cache import (
    add_cached_link,
    get_cached_link_by_slug,
    set_cached_link_invalidated,
    set_cached_links_invalidated,
)
from lnkr.config.application_settings import application_settings

if TYPE_CHECKING:
    import pytest
    from redis.asyncio import Redis

    from lnkr.models import LinkCache


async def test_add_cached_link__existing_entry_not_overwritten(cache: Redis, cached_link: LinkCache) -> None:
    updated_cached_link = cached_link.model_copy(update={"target_url": f"{cached_link.target_url}/updated"})
    _, lease_token = await get_cached_link_by_slug(cache, cached_link.slug)
    assert lease_token is not None
    await add_cached_link(cache, cached_link, lease_token)

    await add_cached_link(cache, updated_cached_link, lease_token)
    result = await get_cached_link_by_slug(cache, cached_link.slug)

    assert result == (cached_link, None)


async def test_add_cached_link__expired_lease_rejected(cache: Redis, cached_link: LinkCache) -> None:
    _, lease_token = await get_cached_link_by_slug(cache, cached_link.slug)
    assert lease_token is not None
    await cache.pexpire(f"link:{cached_link.slug}", 0)

    await add_cached_link(cache, cached_link, lease_token)
    cached_value = await cache.get(f"link:{cached_link.slug}")

    assert cached_value is None


async def test_add_cached_link__replacement_lease_preserved(cache: Redis, cached_link: LinkCache) -> None:
    _, old_lease_token = await get_cached_link_by_slug(cache, cached_link.slug)
    assert old_lease_token is not None
    await cache.pexpire(f"link:{cached_link.slug}", 0)
    _, new_lease_token = await get_cached_link_by_slug(cache, cached_link.slug)

    await add_cached_link(cache, cached_link, old_lease_token)
    cached_value = await cache.get(f"link:{cached_link.slug}")

    assert new_lease_token is not None
    assert new_lease_token != old_lease_token
    assert cached_value == new_lease_token


async def test_add_cached_link__configured_ttl_applied(cache: Redis, cached_link: LinkCache) -> None:
    _, lease_token = await get_cached_link_by_slug(cache, cached_link.slug)
    assert lease_token is not None

    await add_cached_link(cache, cached_link, lease_token)
    result = await get_cached_link_by_slug(cache, cached_link.slug)
    ttl = await cache.ttl(f"link:{cached_link.slug}")

    assert result == (cached_link, None)
    assert 0 < ttl <= application_settings.LINK_CACHE_TTL_SECONDS


async def test_get_cached_link_by_slug__cache_miss_claims_lease(cache: Redis, slug: str) -> None:
    cached_link, lease_token = await get_cached_link_by_slug(cache, slug)
    cached_value = await cache.get(f"link:{slug}")
    ttl = await cache.ttl(f"link:{slug}")

    assert cached_link is None
    assert lease_token is not None
    assert cached_value == lease_token
    assert 0 < ttl <= 5


async def test_get_cached_link_by_slug__existing_lease_preserved(cache: Redis, slug: str) -> None:
    _, lease_token = await get_cached_link_by_slug(cache, slug)
    # Shorten the lease so an accidental reset to five seconds is detectable even when calls happen immediately.
    await cache.pexpire(f"link:{slug}", 4000)
    expires_at = await cache.pexpiretime(f"link:{slug}")

    result = await get_cached_link_by_slug(cache, slug)
    cached_value = await cache.get(f"link:{slug}")
    current_expires_at = await cache.pexpiretime(f"link:{slug}")

    assert result == (None, None)
    assert cached_value == lease_token
    assert current_expires_at == expires_at


async def test_get_cached_link_by_slug__malformed_cached_link(
    cache: Redis,
    slug: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    await cache.set(f"link:{slug}", '{"slug": "slug"}')

    result = await get_cached_link_by_slug(cache, slug)
    cached_value = await cache.get(f"link:{slug}")

    assert result == (None, None)
    assert cached_value is None
    assert (
        "lnkr.cache.link_cache",
        logging.WARNING,
        f"Invalid cached link for slug {slug!r}, discarding entry",
    ) in caplog.record_tuples


async def test_get_cached_link_by_slug__malformed_entry_replacement_preserved(
    cache: Redis,
    cached_link: LinkCache,
) -> None:
    key = f"link:{cached_link.slug}"
    await cache.set(key, '{"slug": "slug"}')
    # Keep the real method so the replacement can call Redis without calling the mock recursively.
    delex = cache.delex

    async def replace_before_delete(name: str, ifeq: str) -> int:
        # Simulate another request replacing the malformed entry after it was read but before cleanup.
        await cache.set(name, cached_link.model_dump_json())
        # The original malformed value no longer matches, so conditional deletion must preserve the replacement.
        return await delex(name, ifeq=ifeq)

    with mock.patch.object(cache, "delex", side_effect=replace_before_delete):
        result = await get_cached_link_by_slug(cache, cached_link.slug)
    cached_value = await cache.get(key)

    assert result == (None, None)
    assert cached_value == cached_link.model_dump_json()


async def test_get_cached_link_by_slug__cache_hit_preserves_entry(cache: Redis, cached_link: LinkCache) -> None:
    await cache.set(f"link:{cached_link.slug}", cached_link.model_dump_json(), ex=30)
    expires_at = await cache.pexpiretime(f"link:{cached_link.slug}")

    result = await get_cached_link_by_slug(cache, cached_link.slug)
    cached_value = await cache.get(f"link:{cached_link.slug}")
    current_expires_at = await cache.pexpiretime(f"link:{cached_link.slug}")

    assert result == (cached_link, None)
    assert cached_value == cached_link.model_dump_json()
    assert current_expires_at == expires_at


async def test_set_cached_link_invalidated__cached_link_removed(cache: Redis, cached_link: LinkCache) -> None:
    await cache.set(f"link:{cached_link.slug}", cached_link.model_dump_json())

    await set_cached_link_invalidated(cache, cached_link.slug)
    cached_value = await cache.get(f"link:{cached_link.slug}")

    assert cached_value is None


async def test_set_cached_link_invalidated__outstanding_lease_revoked(cache: Redis, cached_link: LinkCache) -> None:
    _, lease_token = await get_cached_link_by_slug(cache, cached_link.slug)
    assert lease_token is not None

    await set_cached_link_invalidated(cache, cached_link.slug)
    await add_cached_link(cache, cached_link, lease_token)
    cached_value = await cache.get(f"link:{cached_link.slug}")

    assert cached_value is None


async def test_set_cached_link_invalidated__new_lease_can_fill_immediately(
    cache: Redis,
    cached_link: LinkCache,
) -> None:
    _, old_lease_token = await get_cached_link_by_slug(cache, cached_link.slug)
    assert old_lease_token is not None
    updated_cached_link = cached_link.model_copy(update={"target_url": f"{cached_link.target_url}/updated"})

    await set_cached_link_invalidated(cache, cached_link.slug)
    _, new_lease_token = await get_cached_link_by_slug(cache, cached_link.slug)
    assert new_lease_token is not None
    await add_cached_link(cache, cached_link, old_lease_token)
    await add_cached_link(cache, updated_cached_link, new_lease_token)
    result = await get_cached_link_by_slug(cache, cached_link.slug)

    assert result == (updated_cached_link, None)


async def test_set_cached_links_invalidated__empty_list(cache: Redis, cached_link: LinkCache) -> None:
    await cache.set(f"link:{cached_link.slug}", cached_link.model_dump_json())

    await set_cached_links_invalidated(cache, [])
    result = await get_cached_link_by_slug(cache, cached_link.slug)

    assert result == (cached_link, None)


async def test_set_cached_links_invalidated__all_cached_links_removed(cache: Redis, cached_link: LinkCache) -> None:
    links = [cached_link.model_copy(update={"slug": f"slug-{index}"}) for index in range(10)]
    for link in links:
        await cache.set(f"link:{link.slug}", link.model_dump_json())

    await set_cached_links_invalidated(cache, [link.slug for link in links])

    for link in links:
        cached_value = await cache.get(f"link:{link.slug}")

        assert cached_value is None


async def test_set_cached_links_invalidated__outstanding_leases_revoked(cache: Redis, cached_link: LinkCache) -> None:
    links = [cached_link.model_copy(update={"slug": f"slug-{index}"}) for index in range(10)]
    lease_tokens = []
    for link in links:
        _, lease_token = await get_cached_link_by_slug(cache, link.slug)
        assert lease_token is not None
        lease_tokens.append(lease_token)

    await set_cached_links_invalidated(cache, [link.slug for link in links])
    for link, lease_token in zip(links, lease_tokens, strict=True):
        await add_cached_link(cache, link, lease_token)

    for link in links:
        cached_value = await cache.get(f"link:{link.slug}")

        assert cached_value is None


async def test_set_cached_links_invalidated__unrelated_links_preserved(cache: Redis, cached_link: LinkCache) -> None:
    other_link = cached_link.model_copy(update={"slug": "other-slug"})
    await cache.set(f"link:{cached_link.slug}", cached_link.model_dump_json())
    await cache.set(f"link:{other_link.slug}", other_link.model_dump_json())

    await set_cached_links_invalidated(cache, [other_link.slug])
    result = await get_cached_link_by_slug(cache, cached_link.slug)

    assert result == (cached_link, None)
