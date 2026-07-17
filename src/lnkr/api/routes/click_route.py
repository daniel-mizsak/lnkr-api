"""
API endpoint for managing clicks.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, Query

from lnkr.api.dependencies import get_click_cursor, get_current_user, get_session
from lnkr.config.application_settings import application_settings
from lnkr.exceptions import SlugDoesNotExistError, SlugNotOwnedByUserError
from lnkr.models import ClickCursor, ClickRead, CursorPaginatedRead, User
from lnkr.services.click_service import list_clicks
from lnkr.services.link_service import get_link_validate_user

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix=application_settings.LINKS_PREFIX)


@router.get("/{slug}/clicks")
async def list_clicks_endpoint(
    slug: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
    cursor: Annotated[ClickCursor | None, Depends(get_click_cursor)],
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
) -> CursorPaginatedRead[ClickRead]:
    """List clicks for a given link."""
    try:
        link = await get_link_validate_user(session, slug, user)
    except SlugDoesNotExistError as slug_does_not_exist_error:
        slug_does_not_exist_error.raise_http_exception()
    except SlugNotOwnedByUserError as slug_not_owned_by_user_error:
        slug_not_owned_by_user_error.raise_http_exception()
    clicks, next_cursor = await list_clicks(session, link, limit, cursor)
    return CursorPaginatedRead(
        items=[ClickRead.from_click(click) for click in clicks],
        next_cursor=next_cursor,
    )
