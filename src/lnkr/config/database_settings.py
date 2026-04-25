"""
Database configurations.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from pydantic import SecretStr  # noqa: TC002
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Database configurations."""

    model_config = SettingsConfigDict(case_sensitive=True)

    POSTGRES_HOST: str
    POSTGRES_PORT: int = 5432
    POSTGRES_USERNAME: str
    POSTGRES_PASSWORD: SecretStr
    POSTGRES_DATABASE: str


database_settings = DatabaseSettings()  # ty:ignore[missing-argument]
