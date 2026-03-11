"""
API endpoint for managing clicks.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, Query

from lnkr.api.dependencies import get_current_user, get_session
from lnkr.config import settings
from lnkr.exceptions import SlugDoesNotExistError, SlugNotOwnedByUserError
from lnkr.models import ClickRead, User
from lnkr.services.click_service import list_clicks
from lnkr.services.link_service import get_link_validate_user

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

router = APIRouter(prefix=settings.LINKS_PREFIX)


@router.get("/{slug}/clicks")
def list_clicks_endpoint(
    slug: str,
    session: Annotated[Session, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
    per_page: Annotated[int, Query(ge=1, le=100)] = 10,
    page: Annotated[int, Query(ge=1)] = 1,
) -> list[ClickRead]:
    """List all clicks for a given link."""
    try:
        link = get_link_validate_user(session, slug, user)
    except SlugDoesNotExistError as slug_does_not_exist_error:
        slug_does_not_exist_error.raise_http_exception()
    except SlugNotOwnedByUserError as slug_not_owned_by_user_error:
        slug_not_owned_by_user_error.raise_http_exception()
    clicks = list_clicks(session, link, per_page, page)
    return [ClickRead.from_click(click) for click in clicks]
