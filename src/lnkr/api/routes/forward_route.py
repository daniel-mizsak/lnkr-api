"""
API endpoint for forwarding links.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from lnkr.api.dependencies import get_cache, get_session
from lnkr.config import settings
from lnkr.exceptions import SlugDoesNotExistError
from lnkr.models import ClickCreate
from lnkr.services.click_service import create_click
from lnkr.services.link_service import get_cached_link

if TYPE_CHECKING:
    from redis import Redis
    from sqlmodel import Session

router = APIRouter(prefix=settings.FORWARD_PREFIX)


@router.get("/{slug}")
def forward_to_target_url_endpoint(
    slug: str,
    session: Annotated[Session, Depends(get_session)],
    cache: Annotated[Redis, Depends(get_cache)],
    request: Request,
) -> RedirectResponse:
    """Redirect to the target url of the link with the given slug."""
    try:
        cached_link = get_cached_link(session, cache, slug)
    except SlugDoesNotExistError as slug_does_not_exist_error:
        slug_does_not_exist_error.raise_http_exception()

    ip_address = request.headers.get("x-forwarded-for", "unknown")  # TODO: Maybe split on ',' and take the first part?
    create_click(session, ClickCreate(ip_address=ip_address), cached_link.id)
    return RedirectResponse(url=cached_link.target_url)
