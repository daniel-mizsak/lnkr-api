"""
Data schemas and database models for login token management.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

import uuid
from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from lnkr.config import settings
from lnkr.models.base import Base


class LoginTokenCreate(BaseModel):
    """Login token schema for creating a login token."""

    email: EmailStr = Field(max_length=64)


class LoginToken(Base):
    """Login token model saved in the database."""

    __tablename__ = "login_tokens"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[EmailStr] = mapped_column(String(64), nullable=False)
    token_hash: Mapped[str] = mapped_column(String, index=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=UTC),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
