"""
Data schemas for paginated responses.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from pydantic import BaseModel, Field, computed_field


class PageNumberPaginatedRead[T](BaseModel):
    """Generic schema for reading a page of items."""

    items: list[T]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    per_page: int = Field(ge=1)

    @computed_field
    @property
    def has_next(self) -> bool:
        """Return whether another page exists."""
        return self.page * self.per_page < self.total


class CursorPaginatedRead[T](BaseModel):
    """Generic schema for reading a cursor-paginated collection."""

    items: list[T]
    next_cursor: str | None
