"""
Data schemas and database models for click management.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import BaseModel
from sqlalchemy import DateTime, Enum, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lnkr.models.base import Base
from lnkr.models.constraints import COUNTRY_CODE_LENGTH, IP_ADDRESS_MAX_LENGTH, USER_AGENT_METADATA_MAX_LENGTH

if TYPE_CHECKING:
    from lnkr.models import Link


class ClickSource(StrEnum):
    """Click source enumeration."""

    # Official lnkr application, identified by a valid frontend API key.
    LNKR_APP = "lnkr_app"

    # Public API request without an authenticated API client.
    PUBLIC_API = "public_api"


class ClickCreate(BaseModel):
    """Click schema for creating a click."""

    source: ClickSource
    ip_address: str | None
    browser: str | None
    operating_system: str | None


class ClickRead(BaseModel):
    """Click schema for reading a click."""

    timestamp: datetime
    ip_address: str | None
    country_code: str | None
    browser: str | None
    operating_system: str | None

    @classmethod
    def from_click(cls, click: Click) -> ClickRead:
        """Create a ClickRead instance from a Click instance."""
        return cls(
            timestamp=click.timestamp,
            ip_address=click.ip_address,
            country_code=click.country_code,
            browser=click.browser,
            operating_system=click.operating_system,
        )


class Click(Base):
    """Click model saved in the database."""

    __tablename__ = "clicks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=UTC),
        nullable=False,
    )
    # TODO: Make sure source is added to existing records.
    source: Mapped[ClickSource] = mapped_column(Enum(ClickSource, name="click_source"), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(IP_ADDRESS_MAX_LENGTH), nullable=True)
    country_code: Mapped[str | None] = mapped_column(String(COUNTRY_CODE_LENGTH), nullable=True)
    browser: Mapped[str | None] = mapped_column(String(USER_AGENT_METADATA_MAX_LENGTH), nullable=True)
    operating_system: Mapped[str | None] = mapped_column(String(USER_AGENT_METADATA_MAX_LENGTH), nullable=True)

    link_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("links.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    link: Mapped[Link] = relationship(back_populates="clicks")

    @classmethod
    def from_click_create(cls, click_create: ClickCreate, country_code: str | None, link_id: uuid.UUID) -> Click:
        """Create a Click instance from a ClickCreate instance."""
        return cls(
            source=click_create.source,
            ip_address=click_create.ip_address,
            country_code=country_code,
            browser=click_create.browser,
            operating_system=click_create.operating_system,
            link_id=link_id,
        )
