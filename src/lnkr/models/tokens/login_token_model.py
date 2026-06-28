"""
Data schemas and database models for login token management.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from lnkr.models.base import Base
from lnkr.models.constraints import (
    COUNTRY_CODE_LENGTH,
    IP_ADDRESS_MAX_LENGTH,
    TOKEN_HASH_LENGTH,
    USER_AGENT_METADATA_MAX_LENGTH,
)

if TYPE_CHECKING:
    from lnkr.models.header_model import IpAddress, UserAgent


EMAIL_MAX_LENGTH = 128


class LoginTokenCreate(BaseModel):
    """Login token schema for creating a login token."""

    email: EmailStr = Field(max_length=EMAIL_MAX_LENGTH)


class LoginTokenVerify(BaseModel):
    """Login token schema for verifying a login token."""

    login_token_value: str


# TODO: Remove old login tokens with a scheduled cleanup task.
class LoginToken(Base):
    """Login token model saved in the database."""

    __tablename__ = "login_tokens"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(EMAIL_MAX_LENGTH), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(TOKEN_HASH_LENGTH), unique=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=UTC),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    ip_address: Mapped[str | None] = mapped_column(String(IP_ADDRESS_MAX_LENGTH), nullable=True)
    country_code: Mapped[str | None] = mapped_column(String(COUNTRY_CODE_LENGTH), nullable=True)
    browser: Mapped[str | None] = mapped_column(String(USER_AGENT_METADATA_MAX_LENGTH), nullable=True)
    operating_system: Mapped[str | None] = mapped_column(String(USER_AGENT_METADATA_MAX_LENGTH), nullable=True)

    @classmethod
    def from_login_token_create(
        cls,
        login_token_create: LoginTokenCreate,
        token_hash: str,
        expires_at: datetime,
        ip_address: IpAddress,
        country_code: str | None,
        user_agent: UserAgent,
    ) -> LoginToken:
        """Create a LoginToken instance from a LoginTokenCreate instance."""
        return cls(
            email=login_token_create.email,
            token_hash=token_hash,
            expires_at=expires_at,
            ip_address=ip_address.ip_address,
            country_code=country_code,
            browser=user_agent.browser,
            operating_system=user_agent.operating_system,
        )
