"""
Data schemas and database models for login token management.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

import uuid
from datetime import UTC, datetime, timedelta

from pydantic import EmailStr  # noqa: TC002
from sqlmodel import Column, DateTime, Field, SQLModel

from lnkr.config import settings


class LoginTokenCreate(SQLModel):
    """Login token schema for creating a login token."""

    email: EmailStr = Field(max_length=64)


class LoginToken(SQLModel, table=True):
    """Login token model saved in the database."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: EmailStr = Field(max_length=64)
    token_hash: str = Field(index=True)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    used_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    # TODO: Maybe store additional info like IP address, user agent, etc.

    @property
    def is_valid(self) -> bool:
        """Check if login token is valid (not used and not expired).

        Returns:
            bool: True if valid, False otherwise.
        """
        now = datetime.now(tz=UTC)

        # This is needed as testing uses SQLite, that does not support timezone-aware datetimes.
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)

        return (self.used_at is None) and (now < expires_at)

    def mark_as_used(self) -> None:
        """Mark login token as used by setting used_at to current time.

        Does not commit to database!
        """
        self.used_at = datetime.now(tz=UTC)

    @classmethod
    def from_login_token_create(
        cls,
        login_token_create: LoginTokenCreate,
        token_hash: str,
    ) -> LoginToken:
        """Create a LoginToken instance from a LoginTokenCreate instance."""
        return cls(
            email=login_token_create.email,
            token_hash=token_hash,
            expires_at=datetime.now(tz=UTC) + timedelta(minutes=settings.LOGIN_TOKEN_EXPIRE_MINUTES),
        )
