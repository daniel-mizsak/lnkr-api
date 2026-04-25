"""
High level services for link management.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

import contextlib
from typing import TYPE_CHECKING, Literal

from redis.exceptions import RedisError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from lnkr.cache import link_cache
from lnkr.config.application_settings import application_settings
from lnkr.database import link_database, user_database
from lnkr.exceptions import (
    SlugAlreadyExistsError,
    SlugDoesNotExistError,
    SlugNotOwnedByUserError,
    UserDoesNotExistError,
    UserLinkLimitExceededError,
)
from lnkr.models import Link, LinkCache, LinkCreate, LinkUpdate, User

if TYPE_CHECKING:
    from redis.asyncio import Redis
    from sqlalchemy.ext.asyncio import AsyncSession


async def create_link(session: AsyncSession, link_create: LinkCreate, user: User) -> Link:
    """Create a link in the database."""
    try:
        locked_user = await user_database.get_user_by_id_for_update(session, user.id)
        if locked_user is None:
            await session.rollback()
            raise UserDoesNotExistError.by_id(user_id=user.id)

        if await link_database.count_links_by_user(session, locked_user.id) >= application_settings.USER_LINK_LIMIT:
            email = locked_user.email
            await session.rollback()
            raise UserLinkLimitExceededError(email=email, user_link_limit=application_settings.USER_LINK_LIMIT)

        link = Link.from_link_create(link_create, locked_user)
        await link_database.save_link(session, link)
        await session.commit()
        await session.refresh(link)
    except IntegrityError as integrity_error:
        # TODO: Check for specific integrity error and raise exception accordingly.
        await session.rollback()
        raise SlugAlreadyExistsError(slug=link_create.slug) from integrity_error
    except SQLAlchemyError:
        await session.rollback()
        raise

    return link


async def get_cached_link(session: AsyncSession, cache: Redis, slug: str) -> LinkCache:
    """Get a link from cache or database by its slug."""
    try:
        cached_link = await link_cache.get_cached_link_by_slug(cache, slug)
    except RedisError:
        cached_link = None

    if cached_link is not None:
        return cached_link

    link = await _get_link(session, slug)
    cached_link = LinkCache.from_link(link)
    with contextlib.suppress(RedisError):
        await link_cache.add_cached_link(cache, cached_link)
    return cached_link


async def get_link_validate_user(session: AsyncSession, slug: str, user: User) -> Link:
    """Get a link by slug and validate that it is owned by the user."""
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
    """Update the target url of a link in the database."""
    link = await get_link_validate_user(session, slug, user)
    link.update_from_link_update(link_update)

    try:
        await link_database.save_link(session, link)
        await session.commit()
        await session.refresh(link)
    except SQLAlchemyError:
        await session.rollback()
        raise

    with contextlib.suppress(RedisError):
        # TODO: Make link cache invalidation reliable so stale link targets are not served after update.
        await link_cache.delete_cached_link_by_slug(cache, slug)
    return link


async def delete_link(session: AsyncSession, cache: Redis, slug: str, user: User) -> None:
    """Delete a link from the database."""
    link = await get_link_validate_user(session, slug, user)

    try:
        await link_database.delete_link(session, link)
        await session.commit()
    except SQLAlchemyError:
        await session.rollback()
        raise

    with contextlib.suppress(RedisError):
        # TODO: Make link cache invalidation reliable so stale link targets are not served after delete.
        await link_cache.delete_cached_link_by_slug(cache, slug)


async def list_links(  # noqa: PLR0913
    session: AsyncSession,
    user: User,
    sort: Literal["created_at", "updated_at"],
    direction: Literal["ascending", "descending"],
    per_page: int,
    page: int,
) -> list[Link]:
    """List all links for a given user."""
    per_page = min(per_page, 100)
    return await link_database.list_links_by_user(session, user, sort, direction, per_page, page)
