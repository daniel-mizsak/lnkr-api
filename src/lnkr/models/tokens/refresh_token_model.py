"""
Data schemas and database models for refresh token management.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel
from sqlalchemy import DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from lnkr.models.base import Base


class RefreshTokenRotate(BaseModel):
    """Refresh token schema for rotating a refresh token."""

    refresh_token_value: str


class RefreshTokenRevoke(BaseModel):
    """Refresh token schema for revoking a refresh token."""

    refresh_token_value: str


class RefreshToken(Base):
    """Refresh token model saved in the database."""

    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=UTC),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @classmethod
    def from_user_id(
        cls,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> RefreshToken:
        """Create a RefreshToken instance from a user id and token hash."""
        return cls(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
