"""
Data schemas for access token management.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from datetime import datetime  # noqa: TC003

from pydantic import BaseModel


class AccessTokenPayload(BaseModel):
    """Access token payload schema."""

    sub: str  # user_id
    iat: datetime
    exp: datetime
    type: str
