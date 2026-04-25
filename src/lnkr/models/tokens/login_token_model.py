"""
Data schemas and database models for login token management.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from lnkr.models.base import Base


class LoginTokenCreate(BaseModel):
    """Login token schema for creating a login token."""

    email: EmailStr = Field(max_length=128)


class LoginTokenVerify(BaseModel):
    """Login token schema for verifying a login token."""

    login_token_value: str


# TODO: Remove old login tokens with a scheduled cleanup task.
class LoginToken(Base):
    """Login token model saved in the database."""

    __tablename__ = "login_tokens"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(128), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=UTC),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # TODO: When creating login token store additional info like IP address, user agent, etc.

    @classmethod
    def from_login_token_create(
        cls,
        login_token_create: LoginTokenCreate,
        token_hash: str,
        expires_at: datetime,
    ) -> LoginToken:
        """Create a LoginToken instance from a LoginTokenCreate instance."""
        return cls(
            email=login_token_create.email,
            token_hash=token_hash,
            expires_at=expires_at,
        )
