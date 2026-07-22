"""
Tests for the link cache.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING

from lnkr.cache.link_cache import add_cached_link, get_cached_link_by_slug
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
