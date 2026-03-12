"""
Data schemas and database models for user management.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

import uuid
from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import Enum, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lnkr.models.base import Base

if TYPE_CHECKING:
    from lnkr.models import Link


class UserStatus(StrEnum):
    """User status enumeration."""

    REGULAR = "regular"


class UserCreate(BaseModel):
    """User schema for creating a user."""

    email: EmailStr = Field(max_length=64)


class UserRead(BaseModel):
    """User schema for reading a user."""

    email: EmailStr
    status: UserStatus

    @classmethod
    def from_user(cls, user: User) -> UserRead:
        """Create a UserRead instance from a User instance."""
        return cls(email=user.email, status=user.status)


class User(Base):
    """User model saved in the database."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[EmailStr] = mapped_column(String(64), index=True, unique=True, nullable=False)
    status: Mapped[UserStatus] = mapped_column(Enum(UserStatus), default=UserStatus.REGULAR)
    links: Mapped[list[Link]] = relationship(back_populates="user", cascade="all, delete-orphan")

    @classmethod
    def from_user_create(cls, user_create: UserCreate) -> User:
        """Create a User instance from a UserCreate instance."""
        return cls(email=user_create.email)
