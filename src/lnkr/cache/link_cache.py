"""
Low level cache operations for link management.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

from typing import TYPE_CHECKING, cast

from lnkr.models import LinkCache

if TYPE_CHECKING:
    from redis.asyncio import Redis


# TODO: Add TTL for cached links.
async def add_cached_link(cache: Redis, link_cache: LinkCache) -> None:
    """Add link to cache."""
    await cache.set(f"link:{link_cache.slug}", link_cache.model_dump_json())


async def get_cached_link_by_slug(cache: Redis, slug: str) -> LinkCache | None:
    """Get link from cache by slug."""
    cached_link = await cache.get(f"link:{slug}")
    if cached_link is not None:
        return LinkCache.model_validate_json(cast("str", cached_link))
    return None


async def delete_cached_link_by_slug(cache: Redis, slug: str) -> None:
    """Delete link from cache by slug."""
    await cache.delete(f"link:{slug}")
