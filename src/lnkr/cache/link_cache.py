"""
Low level cache operations for link management.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING, cast

from pydantic import ValidationError

from lnkr.config.application_settings import application_settings
from lnkr.models import LinkCache

if TYPE_CHECKING:
    from redis.asyncio import Redis


async def add_cached_link(cache: Redis, link_cache: LinkCache) -> None:
    """Add link to cache."""
    await cache.set(
        f"link:{link_cache.slug}", link_cache.model_dump_json(), ex=application_settings.LINK_CACHE_TTL_SECONDS
    )


async def get_cached_link_by_slug(cache: Redis, slug: str) -> LinkCache | None:
    """Get link from cache by slug."""
    cached_link = await cache.get(f"link:{slug}")
    if cached_link is None:
        return None

    try:
        return LinkCache.model_validate_json(cast("str", cached_link))
    except ValidationError:
        await delete_cached_link_by_slug(cache, slug)
        return None


async def delete_cached_link_by_slug(cache: Redis, slug: str) -> None:
    """Delete link from cache by slug."""
    await cache.delete(f"link:{slug}")
