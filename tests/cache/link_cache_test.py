"""
Tests for the link cache.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING

from lnkr.cache.link_cache import get_cached_link_by_slug

if TYPE_CHECKING:
    from redis.asyncio import Redis


async def test_get_cached_link_by_slug__malformed_cached_link(cache: Redis, slug: str) -> None:
    await cache.set(f"link:{slug}", '{"slug": "slug"}')

    cached_link = await get_cached_link_by_slug(cache, slug)

    assert cached_link is None
    assert await cache.get(f"link:{slug}") is None


# TODO: Add test for checking TTL.
