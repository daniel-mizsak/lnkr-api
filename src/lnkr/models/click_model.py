"""
Data schemas and database models for click management.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from lnkr.models import Link


class ClickCreate(SQLModel):
    """Click schema for creating a click."""

    ip_address: str


class Click(SQLModel, table=True):
    """Click model saved in the database."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    ip_address: str

    link_id: uuid.UUID = Field(foreign_key="link.id", index=True, ondelete="CASCADE")
    link: Link = Relationship(back_populates="clicks")

    @classmethod
    def from_click_create(cls, click_create: ClickCreate, link_id: uuid.UUID) -> Click:
        """Create a Click instance from a ClickCreate instance."""
        return cls(ip_address=click_create.ip_address, link_id=link_id)


class ClickRead(SQLModel):
    """Click schema for reading a click."""

    timestamp: datetime
    ip_address: str

    @classmethod
    def from_click(cls, click: Click) -> ClickRead:
        """Create a ClickRead instance from a Click instance."""
        return cls(timestamp=click.timestamp, ip_address=click.ip_address)
