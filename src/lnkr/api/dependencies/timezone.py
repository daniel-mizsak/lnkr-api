"""
FastAPI dependency that provides a validated timezone.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import Query

from lnkr.exceptions import TimezoneInvalidError


def get_timezone(timezone: Annotated[str, Query(min_length=1, max_length=64)] = "UTC") -> ZoneInfo:
    """Get a validated IANA timezone from the query parameters."""
    try:
        return ZoneInfo(timezone)
    except ValueError, ZoneInfoNotFoundError:
        TimezoneInvalidError(timezone).raise_http_exception()
