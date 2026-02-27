"""
Data schemas and database models for link management.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

import uuid
from typing import TYPE_CHECKING

from pydantic import HttpUrl  # noqa: TC002
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from lnkr.models import Click, User


class LinkCreate(SQLModel):
    """Link schema for creating a link."""

    slug: str = Field(min_length=4, max_length=16, schema_extra={"pattern": r"^[a-zA-Z0-9-]+$", "examples": ["slug"]})
    target_url: HttpUrl


class Link(SQLModel, table=True):
    """Link model saved in the database."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    slug: str = Field(index=True, unique=True, min_length=4, max_length=16)
    target_url: str
    clicks: list[Click] = Relationship(back_populates="link", cascade_delete=True)

    user_id: uuid.UUID = Field(foreign_key="user.id", index=True, ondelete="CASCADE")
    user: User = Relationship(back_populates="links")

    @classmethod
    def from_link_create(cls, link_create: LinkCreate, user: User) -> Link:
        """Create a Link instance from a LinkCreate instance."""
        return cls(slug=link_create.slug, target_url=str(link_create.target_url), user=user)  # ty:ignore[missing-argument]

    def update_from_link_update(self, link_update: LinkUpdate) -> None:
        """Update the Link instance from a LinkUpdate instance."""
        self.target_url = str(link_update.target_url)


class LinkCache(SQLModel):
    """Link schema for caching a link."""

    id: uuid.UUID
    slug: str
    target_url: str

    @classmethod
    def from_link(cls, link: Link) -> LinkCache:
        """Create a LinkCache instance from a Link instance."""
        return cls(id=link.id, slug=link.slug, target_url=link.target_url)


class LinkRead(SQLModel):
    """Link schema for reading a link."""

    slug: str
    target_url: str

    @classmethod
    def from_link(cls, link: Link) -> LinkRead:
        """Create a LinkRead instance from a Link instance."""
        return cls(slug=link.slug, target_url=link.target_url)


class LinkForward(SQLModel):
    """Link schema for forwarding a link."""

    target_url: str


class LinkUpdate(SQLModel):
    """Link schema for updating a link."""

    target_url: HttpUrl
