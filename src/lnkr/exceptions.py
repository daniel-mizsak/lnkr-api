"""
Project specific exceptions.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

from typing import NoReturn

from fastapi import HTTPException, status


class LnkrError(Exception):
    """Base exception for all lnkr errors."""


class LoginTokenInvalidError(LnkrError):
    """Raised when a login token is invalid or expired."""

    def __init__(self) -> None:
        """Initialize with default error message."""
        msg = "The provided login token is invalid or has expired"
        super().__init__(msg)

    def raise_http_exception(self) -> NoReturn:
        """Raise an http exception."""
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=[
                {
                    "msg": str(self),
                    "type": "login_token_invalid",
                },
            ],
        )


class UserAlreadyExistsError(LnkrError):
    """Raised when a user already exists in the database."""

    def __init__(self, email: str) -> None:
        """Initialize with default error message."""
        msg = f"User '{email}' already exists"
        super().__init__(msg)

    def raise_http_exception(self) -> NoReturn:
        """Raise an http exception."""
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=[
                {
                    "msg": str(self),
                    "type": "user_already_exists",
                },
            ],
        )


class UserDoesNotExistError(LnkrError):
    """Raised when a user does not exist in the database."""

    def __init__(self, email: str) -> None:
        """Initialize with default error message."""
        msg = f"User '{email}' does not exist"
        super().__init__(msg)

    def raise_http_exception(self) -> NoReturn:
        """Raise an http exception."""
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[
                {
                    "msg": str(self),
                    "type": "user_does_not_exist",
                },
            ],
        )


class UserLinkLimitExceededError(LnkrError):
    """Raised when a user exceeds their link limit."""

    def __init__(self, email: str, user_link_limit: int) -> None:
        """Initialize with default error message."""
        msg = f"User '{email}' exceeds their link limit of {user_link_limit}"
        super().__init__(msg)

    def raise_http_exception(self) -> NoReturn:
        """Raise an http exception."""
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=[
                {
                    "msg": str(self),
                    "type": "user_link_limit_exceeded",
                },
            ],
        )


class SlugAlreadyExistsError(LnkrError):
    """Raised when a slug already exists in the database."""

    def __init__(self, slug: str) -> None:
        """Initialize with default error message."""
        msg = f"Slug '{slug}' already exists"
        super().__init__(msg)
        self.slug = slug

    def raise_http_exception(self) -> NoReturn:
        """Raise an http exception."""
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=[
                {
                    "input": self.slug,
                    "loc": ["body", "slug"],
                    "msg": str(self),
                    "type": "slug_already_exists",
                },
            ],
        )


class SlugDoesNotExistError(LnkrError):
    """Raised when a slug does not exist in the database."""

    def __init__(self, slug: str) -> None:
        """Initialize with default error message."""
        msg = f"Slug '{slug}' does not exist"
        super().__init__(msg)
        self.slug = slug

    def raise_http_exception(self) -> NoReturn:
        """Raise an http exception."""
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[
                {
                    "input": self.slug,
                    "loc": ["path", "slug"],
                    "msg": str(self),
                    "type": "slug_does_not_exist",
                },
            ],
        )


class SlugNotOwnedByUserError(LnkrError):
    """Raised when a slug is not owned by the current user."""

    def __init__(self, slug: str) -> None:
        """Initialize with default error message."""
        msg = f"Slug '{slug}' is not owned by the current user"
        super().__init__(msg)
        self.slug = slug

    def raise_http_exception(self) -> NoReturn:
        """Raise an http exception."""
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=[
                {
                    "input": self.slug,
                    "loc": ["path", "slug"],
                    "msg": str(self),
                    "type": "slug_not_owned_by_user",
                },
            ],
        )
