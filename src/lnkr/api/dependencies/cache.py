"""
FastAPI dependency that provides the cache client.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING

from fastapi import Request  # noqa: TC002

if TYPE_CHECKING:
    from redis.asyncio import Redis


async def get_cache(request: Request) -> Redis:
    """Get client for caching operations."""
    client: Redis = request.app.state.cache
    return client
