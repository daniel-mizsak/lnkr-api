"""
Data schemas for header management.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from pydantic import BaseModel


class IpAddress(BaseModel):
    """IP address value parsed from the request header."""

    ip_address: str | None = None


class UserAgent(BaseModel):
    """User agent value parsed from the request header."""

    browser: str | None = None
    operating_system: str | None = None
