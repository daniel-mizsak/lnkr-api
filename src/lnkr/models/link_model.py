"""
Data schemas and database models for link management.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Annotated

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, HttpUrl, model_validator
from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lnkr.models.base import Base

if TYPE_CHECKING:
    from lnkr.models import Click, User


MAX_TARGET_URL_LENGTH = 1024

LinkPassword = Annotated[str, Field(min_length=1, max_length=32)]


class LinkStatus(StrEnum):
    """Link status enumeration."""

    ACTIVE = "active"
    DISABLED = "disabled"


class LinkCreate(BaseModel):
    """Link schema for creating a link."""

    model_config = ConfigDict(extra="forbid")

    slug: str = Field(
        min_length=4,
        max_length=16,
        pattern=r"^[a-zA-Z0-9-]+$",
        json_schema_extra={"examples": ["slug"]},
    )
    target_url: HttpUrl = Field(max_length=MAX_TARGET_URL_LENGTH)
    expires_at: AwareDatetime | None = Field(default=None, json_schema_extra={"examples": [None]})
    password: LinkPassword | None = Field(default=None, json_schema_extra={"examples": [None]})


class LinkRead(BaseModel):
    """Link schema for reading a link."""

    slug: str
    target_url: str
    status: LinkStatus
    expires_at: AwareDatetime | None
    password_protected: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_link(cls, link: Link) -> LinkRead:
        """Create a LinkRead instance from a Link instance."""
        return cls(
            slug=link.slug,
            target_url=link.target_url,
            status=link.status,
            expires_at=link.expires_at,
            password_protected=link.password_hash is not None,
            created_at=link.created_at,
            updated_at=link.updated_at,
        )


class LinkUpdate(BaseModel):
    """Link schema for updating a link."""

    model_config = ConfigDict(extra="forbid")

    target_url: HttpUrl | None = Field(default=None, max_length=MAX_TARGET_URL_LENGTH)
    expires_at: AwareDatetime | None = None
    status: LinkStatus | None = None
    password: LinkPassword | None = None

    @model_validator(mode="after")
    def _validate_partial_update(self) -> LinkUpdate:
        if not self.model_fields_set:
            msg = "At least one field must be provided"
            raise ValueError(msg)
        if "target_url" in self.model_fields_set and self.target_url is None:
            msg = "target_url cannot be cleared"
            raise ValueError(msg)
        if "status" in self.model_fields_set and self.status is None:
            msg = "status cannot be cleared"
            raise ValueError(msg)
        return self


class LinkCache(BaseModel):
    """Link schema for caching a link."""

    id: uuid.UUID
    slug: str
    target_url: str
    status: LinkStatus
    expires_at: AwareDatetime | None
    password_hash: str | None

    @classmethod
    def from_link(cls, link: Link) -> LinkCache:
        """Create a LinkCache instance from a Link instance."""
        return cls(
            id=link.id,
            slug=link.slug,
            target_url=link.target_url,
            status=link.status,
            expires_at=link.expires_at,
            password_hash=link.password_hash,
        )


class LinkUnlock(BaseModel):
    """Link schema for unlocking a password protected link for forwarding."""

    password: LinkPassword


class LinkForward(BaseModel):
    """Link schema for forwarding a link."""

    target_url: str


class Link(Base):
    """Link model saved in the database."""

    __tablename__ = "links"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(16), index=True, unique=True, nullable=False)
    target_url: Mapped[str] = mapped_column(String(MAX_TARGET_URL_LENGTH), nullable=False)
    status: Mapped[LinkStatus] = mapped_column(
        Enum(LinkStatus, name="link_status"),
        default=LinkStatus.ACTIVE,
        nullable=False,
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=UTC),
        onupdate=lambda: datetime.now(tz=UTC),
        nullable=False,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user: Mapped[User] = relationship(back_populates="links")
    clicks: Mapped[list[Click]] = relationship(back_populates="link", cascade="all, delete-orphan")

    @classmethod
    def from_link_create(cls, link_create: LinkCreate, user: User, password_hash: str | None = None) -> Link:
        """Create a Link instance from a LinkCreate instance."""
        return cls(
            slug=link_create.slug,
            target_url=str(link_create.target_url),
            expires_at=link_create.expires_at,
            password_hash=password_hash,
            user=user,
        )

    def update_from_link_update(self, link_update: LinkUpdate, password_hash: str | None = None) -> None:
        """Apply a partial update to the Link instance."""
        fields_set = link_update.model_fields_set
        if "target_url" in fields_set and link_update.target_url is not None:
            self.target_url = str(link_update.target_url)
        if "expires_at" in fields_set:
            self.expires_at = link_update.expires_at
        if "status" in fields_set and link_update.status is not None:
            self.status = link_update.status
        if "password" in fields_set:
            self.password_hash = password_hash
