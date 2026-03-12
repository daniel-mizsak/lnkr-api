"""
Data schemas and database models for link management.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lnkr.models.base import Base

if TYPE_CHECKING:
    from lnkr.models import Click, User


class LinkCreate(BaseModel):
    """Link schema for creating a link."""

    slug: str = Field(
        min_length=4,
        max_length=16,
        pattern=r"^[a-zA-Z0-9-]+$",
        json_schema_extra={"examples": ["slug"]},
    )
    target_url: HttpUrl


class LinkRead(BaseModel):
    """Link schema for reading a link."""

    slug: str
    target_url: str

    @classmethod
    def from_link(cls, link: Link) -> LinkRead:
        """Create a LinkRead instance from a Link instance."""
        return cls(slug=link.slug, target_url=link.target_url)


class LinkUpdate(BaseModel):
    """Link schema for updating a link."""

    target_url: HttpUrl


class LinkCache(BaseModel):
    """Link schema for caching a link."""

    id: uuid.UUID
    slug: str
    target_url: str

    @classmethod
    def from_link(cls, link: Link) -> LinkCache:
        """Create a LinkCache instance from a Link instance."""
        return cls(id=link.id, slug=link.slug, target_url=link.target_url)


class LinkForward(BaseModel):
    """Link schema for forwarding a link."""

    target_url: str


class Link(Base):
    """Link model saved in the database."""

    __tablename__ = "links"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
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
    slug: Mapped[str] = mapped_column(String(16), index=True, unique=True, nullable=False)
    target_url: Mapped[str] = mapped_column(String, nullable=False)

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    user: Mapped[User] = relationship(back_populates="links")
    clicks: Mapped[list[Click]] = relationship(back_populates="link", cascade="all, delete-orphan")

    @classmethod
    def from_link_create(cls, link_create: LinkCreate, user: User) -> Link:
        """Create a Link instance from a LinkCreate instance."""
        return cls(slug=link_create.slug, target_url=str(link_create.target_url), user=user)

    def update_from_link_update(self, link_update: LinkUpdate) -> None:
        """Update the Link instance from a LinkUpdate instance."""
        self.target_url = str(link_update.target_url)
