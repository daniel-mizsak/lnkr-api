"""
Data schemas and database models.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from lnkr.models.click_model import (
    Click,
    ClickAnalyticsCountryCountRead,
    ClickAnalyticsDailyClicksRead,
    ClickAnalyticsDailyCountRead,
    ClickAnalyticsPeriodRead,
    ClickAnalyticsRead,
    ClickAnalyticsRecentClickRead,
    ClickAnalyticsSummaryRead,
    ClickAnalyticsTimeRange,
    ClickAnalyticsTopCountriesRead,
    ClickCreate,
    ClickCursor,
    ClickRead,
    ClickSource,
)
from lnkr.models.header_model import IpAddress, UserAgent
from lnkr.models.link_model import (
    Link,
    LinkCache,
    LinkCreate,
    LinkForward,
    LinkListRead,
    LinkRead,
    LinkStatus,
    LinkUnlock,
    LinkUpdate,
    SlugRead,
)
from lnkr.models.pagination_model import CursorPaginatedRead, PageNumberPaginatedRead
from lnkr.models.tokens import AuthTokensRead
from lnkr.models.tokens.access_token_model import AccessTokenPayload
from lnkr.models.tokens.login_token_model import LoginToken, LoginTokenCreate, LoginTokenVerify
from lnkr.models.tokens.refresh_token_model import RefreshToken, RefreshTokenRevoke, RefreshTokenRotate
from lnkr.models.user_model import User, UserCreate, UserRead, UserStatus

__all__ = [
    "AccessTokenPayload",
    "AuthTokensRead",
    "Click",
    "ClickAnalyticsCountryCountRead",
    "ClickAnalyticsDailyClicksRead",
    "ClickAnalyticsDailyCountRead",
    "ClickAnalyticsPeriodRead",
    "ClickAnalyticsRead",
    "ClickAnalyticsRecentClickRead",
    "ClickAnalyticsSummaryRead",
    "ClickAnalyticsTimeRange",
    "ClickAnalyticsTopCountriesRead",
    "ClickCreate",
    "ClickCursor",
    "ClickRead",
    "ClickSource",
    "CursorPaginatedRead",
    "IpAddress",
    "Link",
    "LinkCache",
    "LinkCreate",
    "LinkForward",
    "LinkListRead",
    "LinkRead",
    "LinkStatus",
    "LinkUnlock",
    "LinkUpdate",
    "LoginToken",
    "LoginTokenCreate",
    "LoginTokenVerify",
    "PageNumberPaginatedRead",
    "RefreshToken",
    "RefreshTokenRevoke",
    "RefreshTokenRotate",
    "SlugRead",
    "User",
    "UserAgent",
    "UserCreate",
    "UserRead",
    "UserStatus",
]
