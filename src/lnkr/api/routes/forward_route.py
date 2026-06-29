"""
API endpoint for forwarding links.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from contextlib import suppress
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, Header, Response
from sqlalchemy.exc import SQLAlchemyError

from lnkr.api.dependencies import (
    get_cache,
    get_geoip_reader,
    get_ip_address,
    get_session,
    get_user_agent,
)
from lnkr.api.dependencies.header import FRONTEND_API_KEY_HEADER, check_frontend_api_key
from lnkr.config.application_settings import application_settings
from lnkr.exceptions import (
    LinkDisabledError,
    LinkExpiredError,
    LinkPasswordInvalidError,
    LinkPasswordRequiredError,
    SlugDoesNotExistError,
)
from lnkr.models import ClickCreate, ClickSource, IpAddress, LinkForward, LinkUnlock, UserAgent
from lnkr.services.click_service import create_click
from lnkr.services.link_service import get_cached_link, get_cached_link_validate_password

if TYPE_CHECKING:
    from geoip2.database import Reader
    from redis.asyncio import Redis
    from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix=application_settings.FORWARD_PREFIX)


def _get_click_source(
    x_frontend_api_key: Annotated[str | None, Header(alias=FRONTEND_API_KEY_HEADER)] = None,
) -> ClickSource:
    if check_frontend_api_key(x_frontend_api_key):
        return ClickSource.LNKR_APP
    return ClickSource.PUBLIC_API


def _set_no_store_header(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


@router.get("/{slug}", dependencies=[Depends(_set_no_store_header)])
async def forward_to_target_url_endpoint(
    slug: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    cache: Annotated[Redis, Depends(get_cache)],
    geoip_reader: Annotated[Reader, Depends(get_geoip_reader)],
    click_source: Annotated[ClickSource, Depends(_get_click_source)],
    ip_address: Annotated[IpAddress, Depends(get_ip_address)],
    user_agent: Annotated[UserAgent, Depends(get_user_agent)],
) -> LinkForward:
    """Return the target url of the link with the given slug."""
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
        await create_click(
            session,
            geoip_reader,
            ClickCreate(
                source=click_source,
                ip_address=ip_address.ip_address,
                browser=user_agent.browser,
                operating_system=user_agent.operating_system,
            ),
            cached_link.id,
        )

    return LinkForward(target_url=cached_link.target_url)


@router.post("/{slug}/unlock", dependencies=[Depends(_set_no_store_header)])
async def unlock_target_url_endpoint(
    slug: str,
    link_unlock: LinkUnlock,
    session: Annotated[AsyncSession, Depends(get_session)],
    cache: Annotated[Redis, Depends(get_cache)],
    geoip_reader: Annotated[Reader, Depends(get_geoip_reader)],
    click_source: Annotated[ClickSource, Depends(_get_click_source)],
    ip_address: Annotated[IpAddress, Depends(get_ip_address)],
    user_agent: Annotated[UserAgent, Depends(get_user_agent)],
) -> LinkForward:
    """Return the target url of the link with the given slug if the provided password is correct."""
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
        await create_click(
            session,
            geoip_reader,
            ClickCreate(
                source=click_source,
                ip_address=ip_address.ip_address,
                browser=user_agent.browser,
                operating_system=user_agent.operating_system,
            ),
            cached_link.id,
        )

    return LinkForward(target_url=cached_link.target_url)
