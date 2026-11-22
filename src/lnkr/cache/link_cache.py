"""
Low level cache operations for link management.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

import logging
import secrets
from typing import TYPE_CHECKING, cast

from pydantic import ValidationError

from lnkr.config.application_settings import application_settings
from lnkr.models import LinkCache

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)

_LINK_LEASE_PREFIX = "pending:"
_LINK_LEASE_TTL_SECONDS = 5


async def add_cached_link(cache: Redis, link_cache: LinkCache, lease_token: str) -> None:
    """Fill the cache only while the reader's lease token is still present."""
    await cache.set(
        f"link:{link_cache.slug}",
        link_cache.model_dump_json(),
        ex=application_settings.LINK_CACHE_TTL_SECONDS,
        ifeq=lease_token,
    )


async def get_cached_link_by_slug(cache: Redis, slug: str) -> tuple[LinkCache | None, str | None]:
    """Get a cached link or claim a lease token before the caller reads the database."""
    lease_token = f"{_LINK_LEASE_PREFIX}{secrets.token_urlsafe(32)}"
    cached_value = await cache.set(
        f"link:{slug}",
        lease_token,
        ex=_LINK_LEASE_TTL_SECONDS,
        nx=True,
        get=True,
    )
    if cached_value is None:
        return None, lease_token

    cached_value = cast("str", cached_value)
    if cached_value.startswith(_LINK_LEASE_PREFIX):
        return None, None

    try:
        return LinkCache.model_validate_json(cached_value), None
    except ValidationError:
        logger.warning("Invalid cached link for slug %r, discarding entry", slug)
        await cache.delex(f"link:{slug}", ifeq=cached_value)
        return None, None


async def set_cached_link_invalidated(cache: Redis, slug: str) -> None:
    """Remove a cached link or revoke its outstanding lease token after a mutation."""
    await cache.delete(f"link:{slug}")


async def set_cached_links_invalidated(cache: Redis, slugs: list[str]) -> None:
    """Remove cached links and revoke their lease tokens in a single batch."""
    async with cache.pipeline(transaction=False) as pipeline:
        for slug in slugs:
            pipeline.delete(f"link:{slug}")
        await pipeline.execute()
