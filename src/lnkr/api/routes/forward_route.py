"""
API endpoint for forwarding links.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

import ipaddress
from contextlib import suppress
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, Header
from sqlalchemy.exc import SQLAlchemyError

from lnkr.api.dependencies import check_frontend_api_key, get_cache, get_session
from lnkr.config.application_settings import application_settings
from lnkr.exceptions import SlugDoesNotExistError
from lnkr.models import ClickCreate, LinkForward
from lnkr.services.click_service import create_click
from lnkr.services.link_service import get_cached_link

if TYPE_CHECKING:
    from redis.asyncio import Redis
    from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix=application_settings.FORWARD_PREFIX)


def _get_ip_address(
    is_frontend: Annotated[bool, Depends(check_frontend_api_key)],
    x_client_ip: Annotated[str | None, Header(alias="X-Client-IP")] = None,
) -> str | None:
    if not is_frontend or x_client_ip is None:
        return None
    try:
        return str(ipaddress.ip_address(x_client_ip.strip()))
    except ValueError:
        return None


# TODO: Add direct forwarding (redirect) option.
@router.get("/{slug}")
async def forward_to_target_url_endpoint(
    slug: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    cache: Annotated[Redis, Depends(get_cache)],
    ip_address: Annotated[str | None, Depends(_get_ip_address)],
) -> LinkForward:
    """Return the target url of the link with the given slug."""
    try:
        cached_link = await get_cached_link(session, cache, slug)
    except SlugDoesNotExistError as slug_does_not_exist_error:
        slug_does_not_exist_error.raise_http_exception()

    with suppress(SQLAlchemyError):
        await create_click(session, ClickCreate(ip_address=ip_address), cached_link.id)

    return LinkForward(target_url=cached_link.target_url)
