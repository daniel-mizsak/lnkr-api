"""
Data schemas and database models for token management.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

from pydantic import BaseModel


class AuthTokensRead(BaseModel):
    """Authentication tokens schema for login and refresh responses."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105


__all__ = [
    "AuthTokensRead",
]
