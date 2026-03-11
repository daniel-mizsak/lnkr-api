"""
Low level database operations for login token management.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

from typing import TYPE_CHECKING

from sqlalchemy import select

from lnkr.models import LoginToken

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def add_login_token(session: Session, login_token: LoginToken) -> LoginToken:
    """Add login token to database."""
    session.add(login_token)
    session.commit()
    session.refresh(login_token)
    return login_token


def get_login_token_by_token_hash(session: Session, token_hash: str) -> LoginToken | None:
    """Get login token from database by token hash."""
    result = session.execute(select(LoginToken).where(LoginToken.token_hash == token_hash).limit(1))
    return result.scalars().first()
