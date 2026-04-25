"""
Application configurations.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from enum import StrEnum

from pydantic import SecretStr  # noqa: TC002
from pydantic_settings import BaseSettings, SettingsConfigDict


class ApplicationEnvironment(StrEnum):
    """Environment enumeration."""

    DEVELOPMENT = "development"
    PRODUCTION = "production"


class ApplicationSettings(BaseSettings):
    """Application configurations."""

    # TODO: Use `secrets_dir="/run/secrets"` for docker secrets in production.
    model_config = SettingsConfigDict(case_sensitive=True)

    # General
    ENVIRONMENT: ApplicationEnvironment
    FRONTEND_APP_URL: str = "https://app.lnkr.by"
    FRONTEND_FORWARD_URL: str = "https://lnkr.by"
    DEVELOPMENT_USER_EMAIL: str = "user@example.com"

    LOGIN_TOKEN_EXPIRE_MINUTES: int = 10
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ACCESS_TOKEN_SECRET_KEY: SecretStr
    ACCESS_TOKEN_ALGORITHM: str = "HS256"  # noqa: S105

    LINK_CACHE_TTL_SECONDS: int = 60 * 60 * 24  # 24 hours

    SENTRY_DSN: SecretStr | None = None

    # User
    USER_LINK_LIMIT: int = 100

    # API
    API_VERSION: str = "v1"
    AUTH_PREFIX: str = "/auth"
    FORWARD_PREFIX: str = "/forward"
    LINKS_PREFIX: str = "/links"
    USER_PREFIX: str = "/user"

    @property
    def API_VERSION_PREFIX(self) -> str:  # noqa: N802
        """Return the path prefix for the configured API version."""
        return f"/{self.API_VERSION}"

    # Redis
    REDIS_HOST: str
    REDIS_PORT: int = 6379
    REDIS_USERNAME: str
    REDIS_PASSWORD: SecretStr
    REDIS_DATABASE_APPLICATION: int = 0

    # SMTP
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USER: str
    SMTP_PASSWORD: SecretStr
    FROM_EMAIL: str = "hello@lnkr.by"


application_settings = ApplicationSettings()  # ty:ignore[missing-argument]
