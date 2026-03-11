"""
High level database operations for link management.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

from typing import TYPE_CHECKING, Literal

from lnkr.cache import link_cache
from lnkr.config import settings
from lnkr.database import link_database
from lnkr.exceptions import (
    SlugAlreadyExistsError,
    SlugDoesNotExistError,
    SlugNotOwnedByUserError,
    UserLinkLimitExceededError,
)
from lnkr.models import Link, LinkCache, LinkCreate, LinkUpdate, User

if TYPE_CHECKING:
    from redis.asyncio import Redis
    from sqlalchemy.ext.asyncio import AsyncSession


async def create_link(session: AsyncSession, link_create: LinkCreate, user: User) -> Link:
    """Create a link in the database.

    Args:
        session (AsyncSession): The database session.
        link_create (LinkCreate): The data model for creating a link.
        user (User): The user who owns the link.

    Raises:
        SlugAlreadyExistsError: If the slug already exists in the database.
        UserLinkLimitExceededError: If the user exceeds their link limit.

    Returns:
        Link: Link object.
    """
    # TODO: Maybe use IntergrityError to make sure there is no race condition when creating a link with the same slug.
    if await link_database.get_link_by_slug(session, link_create.slug) is not None:
        raise SlugAlreadyExistsError(slug=link_create.slug)

    if await link_database.count_links_by_user(session, user) >= settings.USER_LINK_LIMIT:
        raise UserLinkLimitExceededError(email=user.email, user_link_limit=settings.USER_LINK_LIMIT)
    return await link_database.add_link(session, Link.from_link_create(link_create, user))


async def get_cached_link(session: AsyncSession, cache: Redis, slug: str) -> LinkCache:
    """Get a link from cache or database by its slug.

    Args:
        session (AsyncSession): The database session.
        cache (Redis): The cache client.
        slug (str): The reference key of the link.

    Raises:
        SlugDoesNotExistError: If the slug does not exist in the database.

    Returns:
        LinkCache: LinkCache object.
    """
    cached_link = await link_cache.get_cached_link_by_slug(cache, slug)
    if cached_link is not None:
        return cached_link

    link = await _get_link(session, slug)
    cached_link = LinkCache.from_link(link)
    await link_cache.add_cached_link(cache, cached_link)
    return cached_link


async def get_link_validate_user(session: AsyncSession, slug: str, user: User) -> Link:
    """Get a link from the database by its slug and validate that it is owned by the user.

    Args:
        session (AsyncSession): The database session.
        slug (str): The reference key of the link.
        user (User): The user who owns the link.

    Raises:
        SlugDoesNotExistError: If the slug does not exist in the database.
        SlugNotOwnedByUserError: If the slug is not owned by the user.

    Returns:
        Link: Link object.
    """
    link = await _get_link(session, slug)
    if link.user_id != user.id:
        raise SlugNotOwnedByUserError(slug=slug)
    return link


async def _get_link(session: AsyncSession, slug: str) -> Link:
    link = await link_database.get_link_by_slug(session, slug)
    if link is None:
        raise SlugDoesNotExistError(slug=slug)
    return link


async def update_link_target_url(
    session: AsyncSession, cache: Redis, slug: str, link_update: LinkUpdate, user: User
) -> Link:
    """Update the target url of a link in the database.

    Args:
        session (AsyncSession): The database session.
        cache (Redis): The cache client.
        slug (str): The reference key of the link.
        link_update (LinkUpdate): The data model for updating a link.
        user (User): The user who owns the link.

    Raises:
        SlugDoesNotExistError: If the slug does not exist in the database.
        SlugNotOwnedByUserError: If the slug is not owned by the user.

    Returns:
        Link: Updated link object.
    """
    link = await get_link_validate_user(session, slug, user)
    link.update_from_link_update(link_update)
    await link_cache.delete_cached_link_by_slug(cache, slug)
    return await link_database.add_link(session, link)


async def delete_link(session: AsyncSession, cache: Redis, slug: str, user: User) -> None:
    """Delete a link from the database.

    Args:
        session (AsyncSession): The database session.
        cache (Redis): The cache client.
        slug (str): The reference key of the link.
        user (User): The user who owns the link.

    Raises:
        SlugDoesNotExistError: If the slug does not exist in the database.
        SlugNotOwnedByUserError: If the slug is not owned by the user.
    """
    link = await get_link_validate_user(session, slug, user)
    await link_cache.delete_cached_link_by_slug(cache, slug)
    await link_database.delete_link(session, link)


async def list_links(  # noqa: PLR0913
    session: AsyncSession,
    user: User,
    sort: Literal["created_at", "updated_at"],
    direction: Literal["ascending", "descending"],
    per_page: int,
    page: int,
) -> list[Link]:
    """List all links for a given user.

    Args:
        session (AsyncSession): The database session.
        user (User): The user to list links for.
        sort (str): The property to sort the results by.
        direction (str): The order to sort by.
        per_page (int): The number of links to return per page. Maximum is 100.
        page (int): The page number of the links to return.

    Returns:
        list[Link]: A list of link objects.
    """
    per_page = min(per_page, 100)
    return await link_database.list_links_by_user(session, user, sort, direction, per_page, page)
