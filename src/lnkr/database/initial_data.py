"""
Initial development data for the database.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from lnkr.config.application_settings import ApplicationEnvironment, application_settings
from lnkr.database import AsyncSessionLocal, link_database
from lnkr.models import Click, ClickSource, LinkStatus, UserCreate
from lnkr.models import Link as LinkModel
from lnkr.services.link_service import hash_password
from lnkr.services.user_service import get_or_create_user_without_commit

DEVELOPMENT_LINK_PASSWORD = "password"  # noqa: S105


class Country(StrEnum):
    """Country code and matching development IP address."""

    HU = "HU"
    US = "US"
    DE = "DE"
    GB = "GB"
    JP = "JP"

    @property
    def ip_address(self) -> str:
        """Return an IP address located in the country."""
        ip_address = {
            Country.HU: "84.2.44.1",
            Country.US: "8.8.8.8",
            Country.DE: "81.169.145.1",
            Country.GB: "51.140.0.1",
            Country.JP: "133.130.64.0",
        }
        return ip_address[self]


class Browser(StrEnum):
    """Browser names used by development clicks."""

    CHROME = "Chrome"
    SAFARI = "Safari"
    FIREFOX = "Firefox"
    EDGE = "Edge"


class OperatingSystem(StrEnum):
    """Operating system names used by development clicks."""

    WINDOWS = "Windows"
    MACOS = "macOS"
    LINUX = "Linux"
    IOS = "iOS"
    ANDROID = "Android"


@dataclass(frozen=True)
class DevelopmentClick:
    """Configuration for one development click."""

    days_ago: int
    country: Country
    browser: Browser
    operating_system: OperatingSystem
    source: ClickSource


@dataclass(frozen=True)
class DevelopmentLink:
    """Configuration for one development link and its click history."""

    slug: str
    target_url: str
    clicks: tuple[DevelopmentClick, ...]
    favorite: bool = False
    status: LinkStatus = LinkStatus.ACTIVE
    expires_in: timedelta | None = None
    password_protected: bool = False


DEVELOPMENT_LINKS = (
    DevelopmentLink(
        slug="basic-link",
        target_url="https://example.com/basic",
        clicks=(
            DevelopmentClick(0, Country.HU, Browser.CHROME, OperatingSystem.WINDOWS, ClickSource.LNKR_APP),
            DevelopmentClick(1, Country.US, Browser.SAFARI, OperatingSystem.MACOS, ClickSource.LNKR_APP),
            DevelopmentClick(2, Country.DE, Browser.FIREFOX, OperatingSystem.LINUX, ClickSource.LNKR_APP),
        ),
    ),
    DevelopmentLink(
        slug="favorite-link",
        target_url="https://example.com/favorite",
        clicks=(
            DevelopmentClick(0, Country.HU, Browser.CHROME, OperatingSystem.WINDOWS, ClickSource.LNKR_APP),
            DevelopmentClick(0, Country.US, Browser.SAFARI, OperatingSystem.MACOS, ClickSource.LNKR_APP),
            DevelopmentClick(3, Country.DE, Browser.FIREFOX, OperatingSystem.LINUX, ClickSource.LNKR_APP),
            DevelopmentClick(6, Country.GB, Browser.EDGE, OperatingSystem.WINDOWS, ClickSource.LNKR_APP),
        ),
        favorite=True,
    ),
    DevelopmentLink(
        slug="expires-tomorrow",
        target_url="https://example.com/expires/tomorrow",
        clicks=(
            DevelopmentClick(0, Country.HU, Browser.CHROME, OperatingSystem.WINDOWS, ClickSource.LNKR_APP),
            DevelopmentClick(1, Country.US, Browser.SAFARI, OperatingSystem.MACOS, ClickSource.LNKR_APP),
            DevelopmentClick(4, Country.DE, Browser.FIREFOX, OperatingSystem.LINUX, ClickSource.LNKR_APP),
        ),
        expires_in=timedelta(days=1),
    ),
    DevelopmentLink(
        slug="expires-month",
        target_url="https://example.com/expires/month",
        clicks=(
            DevelopmentClick(0, Country.HU, Browser.CHROME, OperatingSystem.WINDOWS, ClickSource.LNKR_APP),
            DevelopmentClick(2, Country.US, Browser.SAFARI, OperatingSystem.MACOS, ClickSource.LNKR_APP),
            DevelopmentClick(7, Country.DE, Browser.FIREFOX, OperatingSystem.LINUX, ClickSource.LNKR_APP),
            DevelopmentClick(14, Country.GB, Browser.EDGE, OperatingSystem.WINDOWS, ClickSource.LNKR_APP),
        ),
        favorite=True,
        expires_in=timedelta(days=30),
    ),
    DevelopmentLink(
        slug="password-link",
        target_url="https://example.com/password",
        clicks=(
            DevelopmentClick(0, Country.HU, Browser.CHROME, OperatingSystem.WINDOWS, ClickSource.LNKR_APP),
            DevelopmentClick(1, Country.US, Browser.SAFARI, OperatingSystem.MACOS, ClickSource.LNKR_APP),
            DevelopmentClick(5, Country.DE, Browser.FIREFOX, OperatingSystem.LINUX, ClickSource.LNKR_APP),
        ),
        password_protected=True,
    ),
    DevelopmentLink(
        slug="private-favorite",
        target_url="https://example.com/private/favorite",
        clicks=(
            DevelopmentClick(0, Country.HU, Browser.CHROME, OperatingSystem.WINDOWS, ClickSource.LNKR_APP),
            DevelopmentClick(0, Country.US, Browser.SAFARI, OperatingSystem.MACOS, ClickSource.LNKR_APP),
            DevelopmentClick(1, Country.DE, Browser.FIREFOX, OperatingSystem.LINUX, ClickSource.LNKR_APP),
            DevelopmentClick(2, Country.GB, Browser.EDGE, OperatingSystem.WINDOWS, ClickSource.LNKR_APP),
            DevelopmentClick(8, Country.JP, Browser.CHROME, OperatingSystem.ANDROID, ClickSource.LNKR_APP),
        ),
        favorite=True,
        password_protected=True,
    ),
    DevelopmentLink(
        slug="disabled-link",
        target_url="https://example.com/disabled",
        clicks=(
            DevelopmentClick(3, Country.HU, Browser.CHROME, OperatingSystem.WINDOWS, ClickSource.LNKR_APP),
            DevelopmentClick(5, Country.US, Browser.SAFARI, OperatingSystem.MACOS, ClickSource.LNKR_APP),
            DevelopmentClick(9, Country.DE, Browser.FIREFOX, OperatingSystem.LINUX, ClickSource.LNKR_APP),
        ),
        status=LinkStatus.DISABLED,
    ),
    DevelopmentLink(
        slug="expired-link",
        target_url="https://example.com/expired",
        clicks=(
            DevelopmentClick(3, Country.HU, Browser.CHROME, OperatingSystem.WINDOWS, ClickSource.LNKR_APP),
            DevelopmentClick(4, Country.US, Browser.SAFARI, OperatingSystem.MACOS, ClickSource.LNKR_APP),
            DevelopmentClick(7, Country.DE, Browser.FIREFOX, OperatingSystem.LINUX, ClickSource.LNKR_APP),
            DevelopmentClick(12, Country.GB, Browser.EDGE, OperatingSystem.WINDOWS, ClickSource.LNKR_APP),
        ),
        expires_in=-timedelta(days=1),
    ),
    DevelopmentLink(
        slug="no-clicks",
        target_url="https://example.com/no-clicks",
        clicks=(),
    ),
    DevelopmentLink(
        slug="few-clicks",
        target_url="https://example.com/few-clicks",
        clicks=(
            DevelopmentClick(0, Country.HU, Browser.CHROME, OperatingSystem.WINDOWS, ClickSource.LNKR_APP),
            DevelopmentClick(4, Country.US, Browser.SAFARI, OperatingSystem.MACOS, ClickSource.LNKR_APP),
        ),
    ),
    DevelopmentLink(
        slug="popular-link",
        target_url="https://example.com/popular",
        clicks=tuple(
            click
            for click, count in (
                (DevelopmentClick(0, Country.HU, Browser.CHROME, OperatingSystem.WINDOWS, ClickSource.LNKR_APP), 4),
                (DevelopmentClick(1, Country.US, Browser.SAFARI, OperatingSystem.MACOS, ClickSource.LNKR_APP), 4),
                (DevelopmentClick(2, Country.DE, Browser.FIREFOX, OperatingSystem.LINUX, ClickSource.LNKR_APP), 2),
                (DevelopmentClick(3, Country.GB, Browser.EDGE, OperatingSystem.WINDOWS, ClickSource.LNKR_APP), 9),
                (DevelopmentClick(4, Country.JP, Browser.CHROME, OperatingSystem.ANDROID, ClickSource.LNKR_APP), 7),
                (DevelopmentClick(5, Country.HU, Browser.SAFARI, OperatingSystem.IOS, ClickSource.LNKR_APP), 6),
                (DevelopmentClick(6, Country.US, Browser.CHROME, OperatingSystem.ANDROID, ClickSource.LNKR_APP), 2),
                (DevelopmentClick(8, Country.DE, Browser.EDGE, OperatingSystem.WINDOWS, ClickSource.LNKR_APP), 6),
                (DevelopmentClick(9, Country.GB, Browser.FIREFOX, OperatingSystem.MACOS, ClickSource.LNKR_APP), 3),
                (DevelopmentClick(10, Country.JP, Browser.SAFARI, OperatingSystem.IOS, ClickSource.LNKR_APP), 9),
                (DevelopmentClick(12, Country.HU, Browser.CHROME, OperatingSystem.WINDOWS, ClickSource.LNKR_APP), 4),
                (DevelopmentClick(13, Country.US, Browser.SAFARI, OperatingSystem.MACOS, ClickSource.LNKR_APP), 2),
                (DevelopmentClick(14, Country.DE, Browser.FIREFOX, OperatingSystem.LINUX, ClickSource.LNKR_APP), 8),
                (DevelopmentClick(15, Country.GB, Browser.EDGE, OperatingSystem.WINDOWS, ClickSource.LNKR_APP), 3),
                (DevelopmentClick(16, Country.JP, Browser.CHROME, OperatingSystem.ANDROID, ClickSource.LNKR_APP), 5),
                (DevelopmentClick(18, Country.HU, Browser.SAFARI, OperatingSystem.IOS, ClickSource.LNKR_APP), 7),
                (DevelopmentClick(19, Country.US, Browser.CHROME, OperatingSystem.ANDROID, ClickSource.LNKR_APP), 3),
                (DevelopmentClick(20, Country.DE, Browser.EDGE, OperatingSystem.WINDOWS, ClickSource.LNKR_APP), 4),
                (DevelopmentClick(21, Country.GB, Browser.FIREFOX, OperatingSystem.MACOS, ClickSource.LNKR_APP), 6),
                (DevelopmentClick(23, Country.JP, Browser.SAFARI, OperatingSystem.IOS, ClickSource.LNKR_APP), 3),
                (DevelopmentClick(24, Country.HU, Browser.CHROME, OperatingSystem.WINDOWS, ClickSource.LNKR_APP), 8),
                (DevelopmentClick(25, Country.US, Browser.SAFARI, OperatingSystem.MACOS, ClickSource.LNKR_APP), 2),
                (DevelopmentClick(27, Country.DE, Browser.FIREFOX, OperatingSystem.LINUX, ClickSource.LNKR_APP), 5),
            )
            for _ in range(count)
        ),
    ),
    DevelopmentLink(
        slug="old-clicks",
        target_url="https://example.com/old-clicks",
        clicks=(
            DevelopmentClick(30, Country.HU, Browser.CHROME, OperatingSystem.WINDOWS, ClickSource.LNKR_APP),
            DevelopmentClick(35, Country.US, Browser.SAFARI, OperatingSystem.MACOS, ClickSource.LNKR_APP),
            DevelopmentClick(45, Country.DE, Browser.FIREFOX, OperatingSystem.LINUX, ClickSource.LNKR_APP),
            DevelopmentClick(60, Country.GB, Browser.EDGE, OperatingSystem.WINDOWS, ClickSource.LNKR_APP),
            DevelopmentClick(90, Country.JP, Browser.CHROME, OperatingSystem.ANDROID, ClickSource.LNKR_APP),
        ),
    ),
    DevelopmentLink(
        slug="country-stats",
        target_url="https://example.com/analytics/countries",
        clicks=(
            DevelopmentClick(0, Country.HU, Browser.CHROME, OperatingSystem.WINDOWS, ClickSource.LNKR_APP),
            DevelopmentClick(0, Country.US, Browser.SAFARI, OperatingSystem.MACOS, ClickSource.LNKR_APP),
            DevelopmentClick(1, Country.DE, Browser.FIREFOX, OperatingSystem.LINUX, ClickSource.LNKR_APP),
            DevelopmentClick(1, Country.GB, Browser.EDGE, OperatingSystem.WINDOWS, ClickSource.LNKR_APP),
            DevelopmentClick(2, Country.JP, Browser.CHROME, OperatingSystem.ANDROID, ClickSource.LNKR_APP),
            DevelopmentClick(3, Country.HU, Browser.SAFARI, OperatingSystem.IOS, ClickSource.LNKR_APP),
            DevelopmentClick(4, Country.US, Browser.CHROME, OperatingSystem.ANDROID, ClickSource.LNKR_APP),
            DevelopmentClick(6, Country.DE, Browser.EDGE, OperatingSystem.WINDOWS, ClickSource.LNKR_APP),
            DevelopmentClick(8, Country.GB, Browser.FIREFOX, OperatingSystem.MACOS, ClickSource.LNKR_APP),
            DevelopmentClick(12, Country.JP, Browser.SAFARI, OperatingSystem.IOS, ClickSource.LNKR_APP),
        ),
    ),
    DevelopmentLink(
        slug="device-stats",
        target_url="https://example.com/analytics/devices",
        clicks=(
            DevelopmentClick(0, Country.HU, Browser.CHROME, OperatingSystem.WINDOWS, ClickSource.LNKR_APP),
            DevelopmentClick(0, Country.US, Browser.SAFARI, OperatingSystem.MACOS, ClickSource.LNKR_APP),
            DevelopmentClick(1, Country.DE, Browser.FIREFOX, OperatingSystem.LINUX, ClickSource.LNKR_APP),
            DevelopmentClick(2, Country.GB, Browser.EDGE, OperatingSystem.WINDOWS, ClickSource.LNKR_APP),
            DevelopmentClick(3, Country.JP, Browser.CHROME, OperatingSystem.ANDROID, ClickSource.LNKR_APP),
            DevelopmentClick(5, Country.HU, Browser.SAFARI, OperatingSystem.IOS, ClickSource.LNKR_APP),
            DevelopmentClick(7, Country.US, Browser.CHROME, OperatingSystem.ANDROID, ClickSource.LNKR_APP),
            DevelopmentClick(10, Country.DE, Browser.EDGE, OperatingSystem.WINDOWS, ClickSource.LNKR_APP),
            DevelopmentClick(15, Country.GB, Browser.FIREFOX, OperatingSystem.MACOS, ClickSource.LNKR_APP),
        ),
    ),
    DevelopmentLink(
        slug="public-api-link",
        target_url="https://example.com/public-api",
        clicks=(
            DevelopmentClick(0, Country.HU, Browser.CHROME, OperatingSystem.WINDOWS, ClickSource.PUBLIC_API),
            DevelopmentClick(1, Country.US, Browser.SAFARI, OperatingSystem.MACOS, ClickSource.PUBLIC_API),
            DevelopmentClick(2, Country.DE, Browser.FIREFOX, OperatingSystem.LINUX, ClickSource.PUBLIC_API),
            DevelopmentClick(3, Country.GB, Browser.EDGE, OperatingSystem.WINDOWS, ClickSource.PUBLIC_API),
            DevelopmentClick(5, Country.JP, Browser.CHROME, OperatingSystem.ANDROID, ClickSource.PUBLIC_API),
            DevelopmentClick(8, Country.HU, Browser.SAFARI, OperatingSystem.IOS, ClickSource.PUBLIC_API),
        ),
    ),
)


async def create_initial_data() -> None:
    """Create initial data in the database for development."""
    if application_settings.ENVIRONMENT != ApplicationEnvironment.DEVELOPMENT:
        return

    now = datetime.now(tz=UTC)
    async with AsyncSessionLocal.begin() as session:
        user = await get_or_create_user_without_commit(
            session,
            UserCreate(email=application_settings.DEVELOPMENT_USER_EMAIL),
        )
        password_hash = await hash_password(DEVELOPMENT_LINK_PASSWORD)

        for development_link in DEVELOPMENT_LINKS:
            if await link_database.get_link_by_slug(session, development_link.slug) is not None:
                continue

            created_at = now - timedelta(days=max((click.days_ago for click in development_link.clicks), default=0) + 1)
            link = LinkModel(
                slug=development_link.slug,
                target_url=development_link.target_url,
                status=development_link.status,
                favorite=development_link.favorite,
                expires_at=now + development_link.expires_in if development_link.expires_in is not None else None,
                password_hash=password_hash if development_link.password_protected else None,
                created_at=created_at,
                updated_at=created_at,
                user=user,
            )
            await link_database.save_link(session, link)
            session.add_all(_create_clicks(link, development_link, now))


def _create_clicks(link: LinkModel, development_link: DevelopmentLink, now: datetime) -> list[Click]:
    """Create click records for a development link."""
    return [
        Click(
            timestamp=now - timedelta(days=click.days_ago),
            source=click.source,
            ip_address=click.country.ip_address,
            country_code=click.country.value,
            browser=click.browser.value,
            operating_system=click.operating_system.value,
            link=link,
        )
        for click in development_link.clicks
    ]
