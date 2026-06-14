"""
High level services for link management.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

import contextlib
import io
import secrets
import string
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal

import segno
from anyio import to_thread
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from redis.exceptions import RedisError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from lnkr.cache import link_cache
from lnkr.config.application_settings import application_settings
from lnkr.database import link_database, user_database
from lnkr.exceptions import (
    LinkDisabledError,
    LinkExpiredError,
    LinkPasswordInvalidError,
    RandomSlugGenerationError,
    SlugAlreadyExistsError,
    SlugDoesNotExistError,
    SlugNotOwnedByUserError,
    UserDoesNotExistError,
    UserLinkLimitExceededError,
)
from lnkr.models import Link, LinkCache, LinkCreate, LinkStatus, LinkUpdate, User

if TYPE_CHECKING:
    from redis.asyncio import Redis
    from sqlalchemy.ext.asyncio import AsyncSession


async def create_link(session: AsyncSession, link_create: LinkCreate, user: User) -> Link:
    """Create a link in the database."""
    password_hash: str | None = None
    if link_create.password is not None:
        password_hash = await _hash_password(link_create.password)

    try:
        locked_user = await user_database.get_user_by_id_for_update(session, user.id)
        if locked_user is None:
            await session.rollback()
            raise UserDoesNotExistError.by_id(user_id=user.id)

        if await link_database.count_links_by_user(session, locked_user.id) >= application_settings.USER_LINK_LIMIT:
            email = locked_user.email
            await session.rollback()
            raise UserLinkLimitExceededError(email=email, user_link_limit=application_settings.USER_LINK_LIMIT)

        link = Link.from_link_create(link_create, locked_user, password_hash=password_hash)
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


async def generate_unused_random_slug(session: AsyncSession) -> str:
    """Generate a random slug that does not currently exist in the database."""
    minimum_random_slug_length = 6
    maximum_unused_random_slug_generation_attempts = 6

    # TODO: Check if the slug contains English slur or other inappropriate content.
    for attempt in range(maximum_unused_random_slug_generation_attempts):
        slug = _generate_random_slug(minimum_random_slug_length + attempt)
        if await link_database.get_link_by_slug(session, slug) is None:
            return slug

    raise RandomSlugGenerationError


def _generate_random_slug(random_slug_length: int) -> str:
    random_slug_alphabet = string.ascii_lowercase + string.ascii_uppercase + string.digits
    return "".join(secrets.choice(random_slug_alphabet) for _ in range(random_slug_length))


async def get_cached_link(session: AsyncSession, cache: Redis, slug: str) -> LinkCache:
    """Get a link from cache or database by its slug."""
    # TODO: Add a fail-closed invalidation marker check before using cached link data.
    # The cache must not be authoritative for security-sensitive fields like password_hash.
    try:
        cached_link = await link_cache.get_cached_link_by_slug(cache, slug)
    except RedisError:
        cached_link = None

    if cached_link is None:
        link = await _get_link(session, slug)
        cached_link = LinkCache.from_link(link)
        with contextlib.suppress(RedisError):
            await link_cache.add_cached_link(cache, cached_link)

    if cached_link.status == LinkStatus.DISABLED:
        raise LinkDisabledError(slug=cached_link.slug)
    if cached_link.expires_at is not None and cached_link.expires_at <= datetime.now(tz=UTC):
        raise LinkExpiredError(slug=cached_link.slug)

    return cached_link


async def get_cached_link_validate_password(session: AsyncSession, cache: Redis, slug: str, password: str) -> LinkCache:
    """Get a link from cache or database by its slug and validate the password if the link is protected."""
    cached_link = await get_cached_link(session, cache, slug)
    if (cached_link.password_hash is not None) and (not await _verify_password(password, cached_link.password_hash)):
        raise LinkPasswordInvalidError(slug=cached_link.slug)
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


async def update_link(session: AsyncSession, cache: Redis, slug: str, link_update: LinkUpdate, user: User) -> Link:
    """Apply a partial update to a link in the database."""
    link = await get_link_validate_user(session, slug, user)
    password_hash: str | None = None
    if ("password" in link_update.model_fields_set) and (link_update.password is not None):
        password_hash = await _hash_password(link_update.password)

    link.update_from_link_update(link_update, password_hash=password_hash)

    try:
        await link_database.save_link(session, link)
        await session.commit()
        await session.refresh(link)
    except SQLAlchemyError:
        await session.rollback()
        raise

    with contextlib.suppress(RedisError):
        # TODO: Make link cache invalidation reliable with a fail-closed invalidation marker.
        # If Redis cannot mark this slug stale, the mutation should not commit password/status changes.
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
        # TODO: Make link cache invalidation reliable with a fail-closed invalidation marker.
        # If Redis cannot mark this slug stale, the mutation should not commit the delete.
        await link_cache.delete_cached_link_by_slug(cache, slug)


async def generate_link_qr_code(session: AsyncSession, slug: str, user: User) -> bytes:
    """Generate a QR code for the frontend URL of a link."""
    link = await get_link_validate_user(session, slug, user)
    short_url = f"{application_settings.FRONTEND_FORWARD_URL}/{link.slug}"
    return await to_thread.run_sync(_generate_qr_code, short_url)


def _generate_qr_code(content: str) -> bytes:
    buffer = io.BytesIO()
    segno.make(content, error="M").save(buffer, kind="png", scale=20)
    return buffer.getvalue()


async def list_links(
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


_password_hasher = PasswordHasher()


async def _hash_password(password: str) -> str:
    return await to_thread.run_sync(_password_hasher.hash, password)


async def _verify_password(password: str, password_hash: str) -> bool:
    try:
        return await to_thread.run_sync(_password_hasher.verify, password_hash, password)
    except VerificationError, InvalidHashError:
        return False
