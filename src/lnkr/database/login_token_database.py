"""
Low level database operations for login token management.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

from typing import TYPE_CHECKING

from sqlalchemy import select

from lnkr.models import LoginToken

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def add_login_token(session: AsyncSession, login_token: LoginToken) -> LoginToken:
    """Add login token to database."""
    session.add(login_token)
    await session.commit()
    await session.refresh(login_token)
    return login_token


async def get_login_token_by_token_hash(session: AsyncSession, token_hash: str) -> LoginToken | None:
    """Get login token from database by token hash."""
    result = await session.execute(select(LoginToken).where(LoginToken.token_hash == token_hash).limit(1))
    return result.scalars().first()
