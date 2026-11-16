"""
FastAPI dependency that provides the geoip reader.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING

from fastapi import Request  # noqa: TC002

if TYPE_CHECKING:
    from geoip2.database import Reader


async def get_geoip_reader(request: Request) -> Reader | None:
    """Get geoip reader for IP lookup operations, if the database is available."""
    reader: Reader | None = request.app.state.geoip_reader
    return reader
