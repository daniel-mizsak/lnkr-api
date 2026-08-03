"""
Data schemas for access token management.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

from datetime import datetime  # noqa: TC003

from pydantic import BaseModel


class AccessTokenPayload(BaseModel):
    """Access token payload schema."""

    sub: str  # user_id
    iat: datetime
    exp: datetime
    type: str
