"""
Project specific exceptions.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING, NoReturn

from fastapi import HTTPException, status

if TYPE_CHECKING:
    import uuid

NO_STORE_HEADERS = {"Cache-Control": "no-store"}


class LnkrError(Exception):
    """Base exception for all lnkr errors."""


class FrontendApiKeyInvalidError(LnkrError):
    """Raised when the frontend api key is invalid."""

    def __init__(self) -> None:
        """Initialize with default error message."""
        msg = "The provided frontend api key is invalid"
        super().__init__(msg)

    def raise_http_exception(self) -> NoReturn:
        """Raise an http exception."""
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=[
                {
                    "msg": str(self),
                    "type": "frontend_api_key_invalid",
                },
            ],
        )


class LoginTokenInvalidError(LnkrError):
    """Raised when a login token is invalid, used or expired."""

    def __init__(self) -> None:
        """Initialize with default error message."""
        msg = "The provided login token is invalid, used or has expired"
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


class RefreshTokenInvalidError(LnkrError):
    """Raised when a refresh token is invalid, used, revoked or expired."""

    def __init__(self) -> None:
        """Initialize with default error message."""
        msg = "The provided refresh token is invalid, used, revoked or has expired"
        super().__init__(msg)

    def raise_http_exception(self) -> NoReturn:
        """Raise an http exception."""
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=[
                {
                    "msg": str(self),
                    "type": "refresh_token_invalid",
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

    def __init__(self, message: str) -> None:
        """Initialize with default error message."""
        super().__init__(message)

    @classmethod
    def by_id(cls, user_id: uuid.UUID) -> UserDoesNotExistError:
        """Initialize with default error message for user id."""
        return cls(f"User with id '{user_id}' does not exist")

    @classmethod
    def by_email(cls, email: str) -> UserDoesNotExistError:
        """Initialize with default error message for user email."""
        return cls(f"User with email '{email}' does not exist")

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


class LinkExpiredError(LnkrError):
    """Raised when a link has passed its expiration date."""

    def __init__(self, slug: str) -> None:
        """Initialize with default error message."""
        msg = f"Link with slug '{slug}' has expired"
        super().__init__(msg)
        self.slug = slug

    def raise_http_exception(self) -> NoReturn:
        """Raise an http exception."""
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=[
                {
                    "msg": str(self),
                    "type": "link_expired",
                },
            ],
            headers=NO_STORE_HEADERS,
        )


class LinkPasswordRequiredError(LnkrError):
    """Raised when a link requires a password to be forwarded."""

    def __init__(self, slug: str) -> None:
        """Initialize with default error message."""
        msg = f"Link with slug '{slug}' requires a password"
        super().__init__(msg)
        self.slug = slug

    def raise_http_exception(self) -> NoReturn:
        """Raise an http exception."""
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=[
                {
                    "msg": str(self),
                    "type": "link_password_required",
                },
            ],
            headers=NO_STORE_HEADERS,
        )


class LinkPasswordInvalidError(LnkrError):
    """Raised when an invalid password is provided for a password protected link."""

    def __init__(self, slug: str) -> None:
        """Initialize with default error message."""
        msg = f"The provided password for link with slug '{slug}' is invalid"
        super().__init__(msg)
        self.slug = slug

    def raise_http_exception(self) -> NoReturn:
        """Raise an http exception."""
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=[
                {
                    "msg": str(self),
                    "type": "link_password_invalid",
                },
            ],
            headers=NO_STORE_HEADERS,
        )


class LinkDisabledError(LnkrError):
    """Raised when a link is disabled by the user."""

    def __init__(self, slug: str) -> None:
        """Initialize with default error message."""
        msg = f"Link with slug '{slug}' is disabled"
        super().__init__(msg)
        self.slug = slug

    def raise_http_exception(self) -> NoReturn:
        """Raise an http exception."""
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=[
                {
                    "msg": str(self),
                    "type": "link_disabled",
                },
            ],
        )
