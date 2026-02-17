"""
Data schemas and database models for access token management.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

from datetime import datetime  # noqa: TC003

from pydantic import BaseModel


class AccessTokenPayload(BaseModel):
    """Access token payload schema."""

    sub: str  # email
    iat: datetime
    exp: datetime
    type: str
