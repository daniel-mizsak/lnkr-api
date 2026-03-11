"""
API endpoints for managing links.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

from typing import TYPE_CHECKING, Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response, status

from lnkr.api.dependencies import get_cache, get_current_user, get_session
from lnkr.config import settings
from lnkr.exceptions import (
    SlugAlreadyExistsError,
    SlugDoesNotExistError,
    SlugNotOwnedByUserError,
    UserLinkLimitExceededError,
)
from lnkr.models import LinkCreate, LinkRead, LinkUpdate, User
from lnkr.services.link_service import (
    create_link,
    delete_link,
    get_link_validate_user,
    list_links,
    update_link_target_url,
)

if TYPE_CHECKING:
    from redis import Redis
    from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix=settings.LINKS_PREFIX)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_link_endpoint(
    link_create: LinkCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> LinkRead:
    """Create a link with a slug that points to the target url."""
    try:
        link = await create_link(session, link_create, user)
    except SlugAlreadyExistsError as slug_already_exists_error:
        slug_already_exists_error.raise_http_exception()
    except UserLinkLimitExceededError as user_link_limit_exceeded_error:
        user_link_limit_exceeded_error.raise_http_exception()
    return LinkRead.from_link(link)


@router.get("/{slug}")
async def get_link_endpoint(
    slug: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> LinkRead:
    """Get a link by its slug."""
    try:
        link = await get_link_validate_user(session, slug, user)
    except SlugDoesNotExistError as slug_does_not_exist_error:
        slug_does_not_exist_error.raise_http_exception()
    except SlugNotOwnedByUserError as slug_not_owned_by_user_error:
        slug_not_owned_by_user_error.raise_http_exception()
    return LinkRead.from_link(link)


@router.patch("/{slug}")
async def update_link_endpoint(
    slug: str,
    link_update: LinkUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    cache: Annotated[Redis, Depends(get_cache)],
    user: Annotated[User, Depends(get_current_user)],
) -> LinkRead:
    """Update the target url of a link."""
    try:
        link = await update_link_target_url(session, cache, slug, link_update, user)
    except SlugDoesNotExistError as slug_does_not_exist_error:
        slug_does_not_exist_error.raise_http_exception()
    except SlugNotOwnedByUserError as slug_not_owned_by_user_error:
        slug_not_owned_by_user_error.raise_http_exception()
    return LinkRead.from_link(link)


@router.delete("/{slug}")
async def delete_link_endpoint(
    slug: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    cache: Annotated[Redis, Depends(get_cache)],
    user: Annotated[User, Depends(get_current_user)],
) -> Response:
    """Delete link."""
    try:
        await delete_link(session, cache, slug, user)
    except SlugDoesNotExistError as slug_does_not_exist_error:
        slug_does_not_exist_error.raise_http_exception()
    except SlugNotOwnedByUserError as slug_not_owned_by_user_error:
        slug_not_owned_by_user_error.raise_http_exception()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("")
async def list_links_endpoint(  # noqa: PLR0913
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
    sort: Annotated[Literal["created_at", "updated_at"], Query()] = "updated_at",
    direction: Annotated[Literal["ascending", "descending"], Query()] = "descending",
    per_page: Annotated[int, Query(ge=1, le=100)] = 10,
    page: Annotated[int, Query(ge=1)] = 1,
) -> list[LinkRead]:
    """List all links that have a target url."""
    links = await list_links(session, user, sort, direction, per_page, page)
    return [LinkRead.from_link(link) for link in links]
