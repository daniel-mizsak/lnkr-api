"""
High level services for login token management.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

import hashlib
import secrets
import string
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from lnkr.config.application_settings import application_settings
from lnkr.database.tokens import login_token_database
from lnkr.exceptions import LoginTokenGenerationError, LoginTokenInvalidError
from lnkr.models import LoginToken

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from lnkr.models import IpAddress, LoginTokenCreate, UserAgent


async def create_and_save_login_token(
    session: AsyncSession,
    login_token_create: LoginTokenCreate,
    ip_address: IpAddress,
    country_code: str | None,
    user_agent: UserAgent,
) -> str:
    """Create a login token and save it to the database."""
    try:
        login_token_value = await _create_login_token_without_commit(
            session,
            login_token_create,
            ip_address,
            country_code,
            user_agent,
        )
        await session.commit()
    except LoginTokenGenerationError, SQLAlchemyError:
        await session.rollback()
        raise

    return login_token_value


async def consume_login_token(session: AsyncSession, login_token_value: str) -> LoginToken:
    """Atomically validate and consume a login token."""
    token_hash = _hash_token(login_token_value)

    try:
        login_token = await login_token_database.consume_login_token(session, token_hash)
        if login_token is None:
            await session.rollback()
            raise LoginTokenInvalidError

        await session.commit()
    except SQLAlchemyError:
        await session.rollback()
        raise

    return login_token


async def _create_login_token_without_commit(
    session: AsyncSession,
    login_token_create: LoginTokenCreate,
    ip_address: IpAddress,
    country_code: str | None,
    user_agent: UserAgent,
) -> str:
    maximum_unique_login_token_generation_attempts = 5

    # TODO: Check if the login token contains English slur or other inappropriate content.
    for _ in range(maximum_unique_login_token_generation_attempts):
        login_token_value = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
        token_hash = _hash_token(login_token_value)

        try:
            async with session.begin_nested():
                expires_at = datetime.now(tz=UTC) + timedelta(minutes=application_settings.LOGIN_TOKEN_EXPIRE_MINUTES)
                await login_token_database.save_login_token(
                    session,
                    LoginToken.from_login_token_create(
                        login_token_create,
                        token_hash,
                        expires_at,
                        ip_address,
                        country_code,
                        user_agent,
                    ),
                )
        except IntegrityError:
            continue
        else:
            return login_token_value

    raise LoginTokenGenerationError


def _hash_token(token_value: str) -> str:
    return hashlib.sha256(token_value.encode()).hexdigest()
