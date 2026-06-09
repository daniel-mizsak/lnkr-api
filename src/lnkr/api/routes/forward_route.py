"""
API endpoint for forwarding links.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

import ipaddress
from contextlib import suppress
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, Header, Response
from sqlalchemy.exc import SQLAlchemyError

from lnkr.api.dependencies import check_frontend_api_key, get_cache, get_geoip_reader, get_session
from lnkr.config.application_settings import application_settings
from lnkr.exceptions import (
    LinkDisabledError,
    LinkExpiredError,
    LinkPasswordInvalidError,
    LinkPasswordRequiredError,
    SlugDoesNotExistError,
)
from lnkr.models import ClickCreate, LinkForward, LinkUnlock
from lnkr.services.click_service import create_click
from lnkr.services.link_service import get_cached_link, get_cached_link_validate_password

if TYPE_CHECKING:
    from geoip2.database import Reader
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
        ip_address = ipaddress.ip_address(x_client_ip.strip())
    except ValueError:
        return None
    # Only record clicks from globally routable addresses.
    if not ip_address.is_global:
        return None
    return str(ip_address)


@router.get("/{slug}")
async def forward_to_target_url_endpoint(
    slug: str,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    cache: Annotated[Redis, Depends(get_cache)],
    geoip_reader: Annotated[Reader, Depends(get_geoip_reader)],
    ip_address: Annotated[str | None, Depends(_get_ip_address)],
) -> LinkForward:
    """Return the target url of the link with the given slug."""
    response.headers["Cache-Control"] = "no-store"
    try:
        cached_link = await get_cached_link(session, cache, slug)
    except SlugDoesNotExistError as slug_does_not_exist_error:
        slug_does_not_exist_error.raise_http_exception()
    except LinkDisabledError as link_disabled_error:
        link_disabled_error.raise_http_exception()
    except LinkExpiredError as link_expired_error:
        link_expired_error.raise_http_exception()

    if cached_link.password_hash is not None:
        LinkPasswordRequiredError(slug=cached_link.slug).raise_http_exception()

    with suppress(SQLAlchemyError):
        await create_click(session, geoip_reader, ClickCreate(ip_address=ip_address), cached_link.id)

    return LinkForward(target_url=cached_link.target_url)


@router.post("/{slug}/unlock")
async def unlock_target_url_endpoint(
    slug: str,
    link_unlock: LinkUnlock,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    cache: Annotated[Redis, Depends(get_cache)],
    geoip_reader: Annotated[Reader, Depends(get_geoip_reader)],
    ip_address: Annotated[str | None, Depends(_get_ip_address)],
) -> LinkForward:
    """Return the target url of the link with the given slug if the provided password is correct."""
    response.headers["Cache-Control"] = "no-store"
    try:
        cached_link = await get_cached_link_validate_password(session, cache, slug, link_unlock.password)
    except SlugDoesNotExistError as slug_does_not_exist_error:
        slug_does_not_exist_error.raise_http_exception()
    except LinkDisabledError as link_disabled_error:
        link_disabled_error.raise_http_exception()
    except LinkExpiredError as link_expired_error:
        link_expired_error.raise_http_exception()
    except LinkPasswordInvalidError as link_password_invalid_error:
        link_password_invalid_error.raise_http_exception()

    with suppress(SQLAlchemyError):
        await create_click(session, geoip_reader, ClickCreate(ip_address=ip_address), cached_link.id)

    return LinkForward(target_url=cached_link.target_url)
