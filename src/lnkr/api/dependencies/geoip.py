"""
FastAPI dependency that provides the geoip reader.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING

from fastapi import Request  # noqa: TC002

if TYPE_CHECKING:
    from geoip2.database import Reader


async def get_geoip_reader(request: Request) -> Reader:
    """Get geoip reader for IP lookup operations."""
    reader: Reader = request.app.state.geoip_reader
    return reader
