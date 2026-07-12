"""
API endpoints for managing links.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING, Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response, status

from lnkr.api.dependencies import get_cache, get_current_user, get_session
from lnkr.config.application_settings import application_settings
from lnkr.exceptions import (
    RandomSlugGenerationError,
    SlugAlreadyExistsError,
    SlugDoesNotExistError,
    SlugNotOwnedByUserError,
    UserDoesNotExistError,
    UserLinkLimitExceededError,
)
from lnkr.models import LinkCreate, LinkRead, LinkUpdate, SlugRead, User
from lnkr.models.link_model import TARGET_URL_MAX_LENGTH
from lnkr.services.link_service import (
    create_link,
    delete_link,
    generate_link_qr_code,
    generate_unused_random_slug,
    get_link_validate_user,
    list_links,
    update_link,
)

if TYPE_CHECKING:
    from redis.asyncio import Redis
    from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix=application_settings.LINKS_PREFIX)


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
    except UserDoesNotExistError as user_does_not_exist_error:
        user_does_not_exist_error.raise_http_exception()
    except UserLinkLimitExceededError as user_link_limit_exceeded_error:
        user_link_limit_exceeded_error.raise_http_exception()
    return LinkRead.from_link(link)


@router.get("/slugs/random", dependencies=[Depends(get_current_user)])
async def get_random_slug_endpoint(
    session: Annotated[AsyncSession, Depends(get_session)],
    response: Response,
) -> SlugRead:
    """Get an unused random slug."""
    response.headers["Cache-Control"] = "no-store"
    try:
        slug = await generate_unused_random_slug(session)
    except RandomSlugGenerationError as random_slug_generation_error:
        random_slug_generation_error.raise_http_exception()
    return SlugRead(slug=slug)


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


@router.get(
    "/{slug}/qr",
    response_class=Response,
    responses={
        status.HTTP_200_OK: {
            "description": "QR code for the frontend URL of the link.",
            "content": {"image/png": {}},
        },
    },
)
async def get_link_qr_code_endpoint(
    slug: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> Response:
    """Get a QR code for the frontend URL of a link."""
    try:
        qr_code = await generate_link_qr_code(session, slug, user)
    except SlugDoesNotExistError as slug_does_not_exist_error:
        slug_does_not_exist_error.raise_http_exception()
    except SlugNotOwnedByUserError as slug_not_owned_by_user_error:
        slug_not_owned_by_user_error.raise_http_exception()
    return Response(
        content=qr_code,
        media_type="image/png",
        headers={
            # The QR code of a slug never changes, so clients can cache it.
            "Cache-Control": "private, max-age=86400",
            "Content-Disposition": f'inline; filename="{slug}.png"',
        },
    )


@router.patch("/{slug}")
async def update_link_endpoint(
    slug: str,
    link_update: LinkUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    cache: Annotated[Redis, Depends(get_cache)],
    user: Annotated[User, Depends(get_current_user)],
) -> LinkRead:
    """Update link."""
    try:
        link = await update_link(session, cache, slug, link_update, user)
    except SlugDoesNotExistError as slug_does_not_exist_error:
        slug_does_not_exist_error.raise_http_exception()
    except SlugNotOwnedByUserError as slug_not_owned_by_user_error:
        slug_not_owned_by_user_error.raise_http_exception()
    return LinkRead.from_link(link)


@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT)
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
async def list_links_endpoint(
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
    search: Annotated[str | None, Query(max_length=TARGET_URL_MAX_LENGTH)] = None,
    favorites_only: Annotated[bool, Query()] = False,  # noqa: FBT002
    sort: Annotated[Literal["created_at", "updated_at"], Query()] = "updated_at",
    direction: Annotated[Literal["ascending", "descending"], Query()] = "descending",
    per_page: Annotated[int, Query(ge=1, le=100)] = 10,
    page: Annotated[int, Query(ge=1)] = 1,
) -> list[LinkRead]:
    """List links, with optional filtering."""
    links = await list_links(session, user, search, favorites_only, sort, direction, per_page, page)
    return [LinkRead.from_link(link) for link in links]
