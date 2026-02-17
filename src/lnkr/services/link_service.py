"""
High level database operations for link management.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

from typing import TYPE_CHECKING

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
    from redis import Redis
    from sqlmodel import Session


def create_link(session: Session, link_create: LinkCreate, user: User) -> Link:
    """Create a link in the database.

    Args:
        session (Session): The database session.
        link_create (LinkCreate): The data model for creating a link.
        user (User): The user who owns the link.

    Raises:
        SlugAlreadyExistsError: If the slug already exists in the database.
        UserLinkLimitExceededError: If the user exceeds their link limit.

    Returns:
        Link: Link object.
    """
    # TODO: Maybe use IntergrityError to make sure there is no race condition when creating a link with the same slug.
    if link_database.get_link_by_slug(session, link_create.slug) is not None:
        raise SlugAlreadyExistsError(slug=link_create.slug)

    if link_database.count_links_by_user(session, user) >= settings.USER_LINK_LIMIT:
        raise UserLinkLimitExceededError(email=user.email, user_link_limit=settings.USER_LINK_LIMIT)
    return link_database.add_link(session, Link.from_link_create(link_create, user))


def get_cached_link(session: Session, cache: Redis, slug: str) -> LinkCache:
    """Get a link from cache or database by its slug.

    Args:
        session (Session): The database session.
        cache (Redis): The cache client.
        slug (str): The reference key of the link.

    Raises:
        SlugDoesNotExistError: If the slug does not exist in the database.

    Returns:
        LinkCache: LinkCache object.
    """
    cached_link = link_cache.get_cached_link_by_slug(cache, slug)
    if cached_link is not None:
        return cached_link

    link = _get_link(session, slug)
    cached_link = LinkCache.from_link(link)
    link_cache.add_cached_link(cache, cached_link)
    return cached_link


def get_link_validate_user(session: Session, slug: str, user: User) -> Link:
    """Get a link from the database by its slug and validate that it is owned by the user.

    Args:
        session (Session): The database session.
        slug (str): The reference key of the link.
        user (User): The user who owns the link.

    Raises:
        SlugDoesNotExistError: If the slug does not exist in the database.
        SlugNotOwnedByUserError: If the slug is not owned by the user.

    Returns:
        Link: Link object.
    """
    link = _get_link(session, slug)
    if link.user_id != user.id:
        raise SlugNotOwnedByUserError(slug=slug)
    return link


def _get_link(session: Session, slug: str) -> Link:
    link = link_database.get_link_by_slug(session, slug)
    if link is None:
        raise SlugDoesNotExistError(slug=slug)
    return link


def update_link_target_url(session: Session, cache: Redis, slug: str, link_update: LinkUpdate, user: User) -> Link:
    """Update the target url of a link in the database.

    Args:
        session (Session): The database session.
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
    link = get_link_validate_user(session, slug, user)
    link.update_from_link_update(link_update)
    link_cache.delete_cached_link_by_slug(cache, slug)
    return link_database.add_link(session, link)


def delete_link(session: Session, cache: Redis, slug: str, user: User) -> None:
    """Delete a link from the database.

    Args:
        session (Session): The database session.
        cache (Redis): The cache client.
        slug (str): The reference key of the link.
        user (User): The user who owns the link.

    Raises:
        SlugDoesNotExistError: If the slug does not exist in the database.
        SlugNotOwnedByUserError: If the slug is not owned by the user.
    """
    link = get_link_validate_user(session, slug, user)
    link_cache.delete_cached_link_by_slug(cache, slug)
    link_database.delete_link(session, link)


def list_links(session: Session, user: User, per_page: int, page: int) -> list[Link]:
    """List all links for a given user.

    Args:
        session (Session): The database session.
        user (User): The user to list links for.
        per_page (int): The number of links to return per page. Maximum is 100.
        page (int): The page number of the links to return.

    Returns:
        list[Link]: A list of link objects.
    """
    per_page = min(per_page, 100)
    return link_database.list_links_by_user(session, user, per_page, page)
