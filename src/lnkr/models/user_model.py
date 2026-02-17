"""
Data schemas and database models for user management.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

import uuid
from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import EmailStr  # noqa: TC002
from sqlmodel import Column, Enum, Field, Relationship, SQLModel

if TYPE_CHECKING:
    from lnkr.models import Link


class UserStatus(StrEnum):
    """User status enumeration."""

    REGULAR = "regular"


class UserCreate(SQLModel):
    """User schema for creating a user."""

    email: EmailStr = Field(max_length=64)


class User(SQLModel, table=True):
    """User model saved in the database."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: EmailStr = Field(index=True, unique=True, max_length=64)
    status: UserStatus = Field(default=UserStatus.REGULAR, sa_column=Column(Enum(UserStatus)))
    links: list[Link] = Relationship(back_populates="user", cascade_delete=True)

    @classmethod
    def from_user_create(cls, user_create: UserCreate) -> User:
        """Create a User instance from a UserCreate instance."""
        return cls(email=user_create.email)
