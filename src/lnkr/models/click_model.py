"""
Data schemas and database models for click management.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel
from sqlalchemy import DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lnkr.models.base import Base

if TYPE_CHECKING:
    from lnkr.models import Link


class ClickCreate(BaseModel):
    """Click schema for creating a click."""

    ip_address: str


class ClickRead(BaseModel):
    """Click schema for reading a click."""

    timestamp: datetime
    ip_address: str

    @classmethod
    def from_click(cls, click: Click) -> ClickRead:
        """Create a ClickRead instance from a Click instance."""
        return cls(timestamp=click.timestamp, ip_address=click.ip_address)


class Click(Base):
    """Click model saved in the database."""

    __tablename__ = "clicks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=UTC),
        nullable=False,
    )
    ip_address: Mapped[str] = mapped_column(String, nullable=False)

    link_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("links.id", ondelete="CASCADE"), index=True)
    link: Mapped[Link] = relationship(back_populates="clicks")

    @classmethod
    def from_click_create(cls, click_create: ClickCreate, link_id: uuid.UUID) -> Click:
        """Create a Click instance from a ClickCreate instance."""
        return cls(ip_address=click_create.ip_address, link_id=link_id)
