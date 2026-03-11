"""
Project configurations.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

from enum import StrEnum

from pydantic import PostgresDsn, computed_field
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    """Environment enumeration."""

    DEVELOPMENT = "development"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Lnkr configurations."""

    # TODO: Use `secrets_dir="/run/secrets"` for docker secrets in production.
    model_config = SettingsConfigDict(case_sensitive=True)

    # General
    ENVIRONMENT: Environment
    FRONTEND_APP_URL: str = "https://app.lnkr.by"
    FRONTEND_FORWARD_URL: str = "https://lnkr.by"
    DEVELOPMENT_USER_EMAIL: str = "user@example.com"

    LOGIN_TOKEN_EXPIRE_MINUTES: int = 10

    ACCESS_TOKEN_EXPIRE_DAYS: int = 7
    ACCESS_TOKEN_SECRET_KEY: str
    ACCESS_TOKEN_ALGORITHM: str = "HS256"  # noqa: S105

    SENTRY_DSN: str | None = None

    USER_LINK_LIMIT: int = 100

    # API
    API_VERSION: str = "v1"
    API_VERSION_PREFIX: str = f"/{API_VERSION}"
    AUTH_PREFIX: str = "/auth"
    FORWARD_PREFIX: str = "/forward"
    LINKS_PREFIX: str = "/links"
    USER_PREFIX: str = "/user"

    # Postgres
    POSTGRES_HOST: str
    POSTGRES_PORT: int = 5432
    POSTGRES_USERNAME: str
    POSTGRES_PASSWORD: str
    POSTGRES_DATABASE: str

    @computed_field
    @property
    def DATABASE_URL(self) -> PostgresDsn:  # noqa: N802
        """Generate the database url from the connection parameters."""
        return PostgresDsn(
            MultiHostUrl.build(
                scheme="postgresql+psycopg",
                username=self.POSTGRES_USERNAME,
                password=self.POSTGRES_PASSWORD,
                host=self.POSTGRES_HOST,
                port=self.POSTGRES_PORT,
                path=self.POSTGRES_DATABASE,
            ),
        )

    # Redis
    REDIS_HOST: str
    REDIS_PORT: int = 6379
    REDIS_USERNAME: str
    REDIS_PASSWORD: str

    @computed_field
    @property
    def REDIS_URL(self) -> str:  # noqa: N802
        """Generate the redis url from the connection parameters."""
        return f"redis://{self.REDIS_USERNAME}:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    # SMTP
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USER: str
    SMTP_PASSWORD: str
    FROM_EMAIL: str = "hello@lnkr.by"


settings = Settings()  # type: ignore[call-arg]
