"""
Data schemas and database models for click management.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

import base64
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import AwareDatetime, BaseModel, Field
from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lnkr.models.base import Base
from lnkr.models.constraints import COUNTRY_CODE_LENGTH, IP_ADDRESS_MAX_LENGTH, USER_AGENT_METADATA_MAX_LENGTH

if TYPE_CHECKING:
    from lnkr.models import Link


CLICK_CURSOR_MAX_LENGTH = 512


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


class ClickCursor(BaseModel):
    """Opaque cursor values for listing clicks."""

    timestamp: AwareDatetime
    id: uuid.UUID

    @classmethod
    def from_click(cls, click: Click) -> ClickCursor:
        """Create a cursor from a click."""
        return cls(timestamp=click.timestamp, id=click.id)

    def encode(self) -> str:
        """Encode the cursor as an opaque URL-safe string."""
        return base64.urlsafe_b64encode(self.model_dump_json().encode()).decode()

    @classmethod
    def decode(cls, cursor: str) -> ClickCursor:
        """Decode and validate an opaque cursor string."""
        decoded = base64.urlsafe_b64decode(cursor)
        return cls.model_validate_json(decoded)


@dataclass(frozen=True)
class ClickAnalyticsTimeRange:
    """Datetime range used by click analytics queries."""

    start: datetime
    end: datetime


class ClickAnalyticsPeriodRead(BaseModel):
    """Effective local-date range represented by an analytics response section."""

    from_date: date
    through_date: date
    timezone: str


class ClickAnalyticsSummaryRead(BaseModel):
    """Reusable headline click statistics."""

    total_clicks: int = Field(ge=0)
    last_7_days_clicks: int = Field(ge=0)


class ClickAnalyticsDailyCountRead(BaseModel):
    """Number of clicks recorded on a calendar day."""

    date: date
    clicks: int = Field(ge=0)


class ClickAnalyticsDailyClicksRead(BaseModel):
    """Daily click counts and the effective period used to calculate them."""

    period: ClickAnalyticsPeriodRead
    days: list[ClickAnalyticsDailyCountRead]


class ClickAnalyticsRecentClickRead(BaseModel):
    """Recent click information displayed in analytics."""

    timestamp: datetime
    country_code: str | None


class ClickAnalyticsCountryCountRead(BaseModel):
    """Click count and share of trusted clicks with a known country."""

    country_code: str
    clicks: int = Field(ge=0)
    percentage: float = Field(ge=0, le=100)


class ClickAnalyticsTopCountriesRead(BaseModel):
    """Top countries and the effective period used to calculate them."""

    period: ClickAnalyticsPeriodRead
    located_click_count: int = Field(ge=0)
    countries: list[ClickAnalyticsCountryCountRead]


class ClickAnalyticsRead(BaseModel):
    """Click analytics dashboard data."""

    summary: ClickAnalyticsSummaryRead
    daily_clicks: ClickAnalyticsDailyClicksRead
    recent_clicks: list[ClickAnalyticsRecentClickRead]
    top_countries: ClickAnalyticsTopCountriesRead


class Click(Base):
    """Click model saved in the database."""

    __tablename__ = "clicks"
    __table_args__ = (
        Index(
            "ix_clicks_link_id_source_timestamp_id",
            "link_id",
            "source",
            "timestamp",
            "id",
        ),
    )

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
