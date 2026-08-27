"""
Low level cache operations for link management.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING, cast

from pydantic import ValidationError

from lnkr.config.application_settings import application_settings
from lnkr.models import LinkCache

if TYPE_CHECKING:
    from redis.asyncio import Redis

_LINK_INVALIDATED = "invalidated"
_LINK_INVALIDATION_TTL_SECONDS = 5


async def add_cached_link(cache: Redis, link_cache: LinkCache) -> None:
    """Fill the cache for a link, without overwriting an existing entry."""
    await cache.set(
        f"link:{link_cache.slug}",
        link_cache.model_dump_json(),
        ex=application_settings.LINK_CACHE_TTL_SECONDS,
        nx=True,
    )


async def get_cached_link_by_slug(cache: Redis, slug: str) -> LinkCache | None:
    """Get link from cache by slug."""
    cached_link = await cache.get(f"link:{slug}")
    if cached_link is None or cached_link == _LINK_INVALIDATED:
        return None

    try:
        return LinkCache.model_validate_json(cast("str", cached_link))
    except ValidationError:
        await cache.delete(f"link:{slug}")
        return None


async def set_cached_link_invalidated(cache: Redis, slug: str) -> None:
    """Mark a slug as invalidated so stale cache fills cannot overwrite a mutation."""
    await cache.set(
        f"link:{slug}",
        _LINK_INVALIDATED,
        ex=_LINK_INVALIDATION_TTL_SECONDS,
    )
