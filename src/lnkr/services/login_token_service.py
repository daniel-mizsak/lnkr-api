"""
High level database operations for login token management.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

import hashlib
import secrets
import string
from typing import TYPE_CHECKING

from lnkr.database import login_token_database
from lnkr.exceptions import LoginTokenInvalidError
from lnkr.models import LoginToken, LoginTokenCreate

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def create_and_save_login_token(session: AsyncSession, login_token_create: LoginTokenCreate) -> str:
    """Create a login token and save it to the database.

    Args:
        session (AsyncSession): The database session.
        login_token_create (LoginTokenCreate): The data model for creating a login token.

    Returns:
        str: The plain login token value.
    """
    login_token_value = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    # No need to further encrypt as tokens are short-lived.
    token_hash = hashlib.sha256(login_token_value.encode()).hexdigest()
    await login_token_database.add_login_token(
        session, LoginToken.from_login_token_create(login_token_create, token_hash)
    )
    return login_token_value


async def validate_login_token(session: AsyncSession, login_token_value: str) -> LoginToken:
    """Validate login token validity.

    Args:
        session (AsyncSession): The database session.
        login_token_value (str): The plain login token value.

    Raises:
        LoginTokenInvalidError: If the login token is invalid.

    Returns:
        LoginToken: The valid login token object.
    """
    token_hash = hashlib.sha256(login_token_value.encode()).hexdigest()
    login_token = await login_token_database.get_login_token_by_token_hash(session, token_hash)
    if (login_token is None) or (not login_token.is_valid):
        raise LoginTokenInvalidError
    return login_token


async def mark_login_token_as_used(session: AsyncSession, login_token: LoginToken) -> None:
    """Mark login token as used.

    Args:
        session (AsyncSession): The database session.
        login_token (LoginToken): The login token object.
    """
    login_token.mark_as_used()
    await login_token_database.add_login_token(session, login_token)
