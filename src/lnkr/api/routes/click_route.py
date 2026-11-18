"""
API endpoint for managing clicks.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, Query

from lnkr.api.dependencies import get_click_cursor, get_current_user, get_session, get_timezone
from lnkr.config.application_settings import application_settings
from lnkr.models import ClickAnalyticsRead, ClickCursor, ClickRead, CursorPaginatedRead, User
from lnkr.services.click_service import get_click_analytics, list_clicks
from lnkr.services.link_service import get_link_validate_user

if TYPE_CHECKING:
    from zoneinfo import ZoneInfo

    from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix=application_settings.LINKS_PREFIX)


@router.get("/{slug}/analytics")
async def get_click_analytics_endpoint(
    slug: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
    timezone: Annotated[ZoneInfo, Depends(get_timezone)],
) -> ClickAnalyticsRead:
    """Get click analytics dashboard data."""
    link = await get_link_validate_user(session, slug, user)
    return await get_click_analytics(session, link, timezone)


@router.get("/{slug}/clicks")
async def list_clicks_endpoint(
    slug: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
    cursor: Annotated[ClickCursor | None, Depends(get_click_cursor)],
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
) -> CursorPaginatedRead[ClickRead]:
    """List clicks for a given link."""
    link = await get_link_validate_user(session, slug, user)
    clicks, next_cursor = await list_clicks(session, link, limit, cursor)
    return CursorPaginatedRead(
        items=[ClickRead.from_click(click) for click in clicks],
        next_cursor=next_cursor,
    )
