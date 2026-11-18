"""
Project specific exceptions.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import uuid


class LnkrError(Exception):
    """Base exception for all lnkr errors."""


class FrontendApiKeyInvalidError(LnkrError):
    """Raised when the frontend api key is invalid."""

    def __init__(self) -> None:
        """Initialize with default error message."""
        msg = "The provided frontend api key is invalid"
        super().__init__(msg)


class CursorInvalidError(LnkrError):
    """Raised when a pagination cursor is invalid."""

    def __init__(self, cursor: str) -> None:
        """Initialize with default error message."""
        msg = "The provided cursor is invalid"
        super().__init__(msg)
        self.cursor = cursor


class LoginTokenInvalidError(LnkrError):
    """Raised when a login token is invalid, used or expired."""

    def __init__(self) -> None:
        """Initialize with default error message."""
        msg = "The provided login token is invalid, used or has expired"
        super().__init__(msg)


class LoginTokenGenerationFailedError(LnkrError):
    """Raised when a unique login token cannot be generated."""

    def __init__(self) -> None:
        """Initialize with default error message."""
        msg = "Unable to generate a login token. Please try again."
        super().__init__(msg)


class LoginTokenDeliveryFailedError(LnkrError):
    """Raised when the login token email cannot be sent."""

    def __init__(self) -> None:
        """Initialize with default error message."""
        msg = "Unable to send a login token. Please request a new token in 60 seconds."
        super().__init__(msg)


class RefreshTokenInvalidError(LnkrError):
    """Raised when a refresh token is invalid, used, revoked or expired."""

    def __init__(self) -> None:
        """Initialize with default error message."""
        msg = "The provided refresh token is invalid, used, revoked or has expired"
        super().__init__(msg)


class RefreshTokenGenerationFailedError(LnkrError):
    """Raised when a unique refresh token cannot be generated."""

    def __init__(self) -> None:
        """Initialize with default error message."""
        msg = "Unable to generate a refresh token. Please try again."
        super().__init__(msg)


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


class UserLinkLimitExceededError(LnkrError):
    """Raised when a user exceeds their link limit."""

    def __init__(self, email: str, user_link_limit: int) -> None:
        """Initialize with default error message."""
        msg = f"User '{email}' exceeds their link limit of {user_link_limit}"
        super().__init__(msg)


class TimezoneInvalidError(LnkrError):
    """Raised when an invalid IANA timezone is provided."""

    def __init__(self, timezone: str) -> None:
        """Initialize with default error message."""
        msg = f"Timezone '{timezone}' is invalid"
        super().__init__(msg)
        self.timezone = timezone


class SlugAlreadyExistsError(LnkrError):
    """Raised when a slug already exists in the database."""

    def __init__(self, slug: str) -> None:
        """Initialize with default error message."""
        msg = f"Slug '{slug}' already exists"
        super().__init__(msg)
        self.slug = slug


class SlugDoesNotExistError(LnkrError):
    """Raised when a slug does not exist in the database."""

    def __init__(self, slug: str) -> None:
        """Initialize with default error message."""
        msg = f"Slug '{slug}' does not exist"
        super().__init__(msg)
        self.slug = slug


class SlugNotOwnedByUserError(LnkrError):
    """Raised when a slug is not owned by the current user."""

    def __init__(self, slug: str) -> None:
        """Initialize with default error message."""
        msg = f"Slug '{slug}' is not owned by the current user"
        super().__init__(msg)
        self.slug = slug


class RandomSlugGenerationFailedError(LnkrError):
    """Raised when an unused random slug cannot be generated."""

    def __init__(self) -> None:
        """Initialize with default error message."""
        msg = "Unable to generate an unused random slug. Please try again."
        super().__init__(msg)


class LinkExpiredError(LnkrError):
    """Raised when a link has passed its expiration date."""

    def __init__(self, slug: str) -> None:
        """Initialize with default error message."""
        msg = f"Link with slug '{slug}' has expired"
        super().__init__(msg)
        self.slug = slug


class LinkPasswordRequiredError(LnkrError):
    """Raised when a link requires a password to be forwarded."""

    def __init__(self, slug: str) -> None:
        """Initialize with default error message."""
        msg = f"Link with slug '{slug}' requires a password"
        super().__init__(msg)
        self.slug = slug


class LinkPasswordInvalidError(LnkrError):
    """Raised when an invalid password is provided for a password protected link."""

    def __init__(self, slug: str) -> None:
        """Initialize with default error message."""
        msg = f"The provided password for link with slug '{slug}' is invalid"
        super().__init__(msg)
        self.slug = slug


class LinkDisabledError(LnkrError):
    """Raised when a link is disabled by the user."""

    def __init__(self, slug: str) -> None:
        """Initialize with default error message."""
        msg = f"Link with slug '{slug}' is disabled"
        super().__init__(msg)
        self.slug = slug


class AccessCredentialsMissingError(LnkrError):
    """Raised when access credentials are missing."""

    def __init__(self) -> None:
        """Initialize with default error message."""
        super().__init__("Not authenticated")


class AccessTokenMissingError(LnkrError):
    """Raised when an access token is missing."""

    def __init__(self) -> None:
        """Initialize with default error message."""
        super().__init__("Authorization token is missing")


class AccessTokenInvalidError(LnkrError):
    """Raised when an access token is invalid."""

    def __init__(self) -> None:
        """Initialize with default error message."""
        super().__init__("Invalid token")


class AccessTokenSubjectInvalidError(LnkrError):
    """Raised when an access token subject is invalid."""

    def __init__(self) -> None:
        """Initialize with default error message."""
        super().__init__("Invalid token")
