"""
Tests for the lnkr configurations.

These tests ensure that changes to the default configurations will break the tests.
Otherwise, (since the api tests are using references to the default values) the tests
will pass in case of an accidental change.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

from lnkr.config import Environment, settings


def test_environment() -> None:
    assert set(Environment.__members__.keys()) == {"DEVELOPMENT", "PRODUCTION"}

    assert Environment.DEVELOPMENT.value == "development"
    assert Environment.PRODUCTION.value == "production"


def test_settings() -> None:
    # General
    assert settings.ENVIRONMENT == Environment.DEVELOPMENT
    assert settings.FRONTEND_URL == "https://lnkr.by"
    assert settings.DEVELOPMENT_USER_EMAIL == "user@example.com"

    assert settings.LOGIN_TOKEN_EXPIRE_MINUTES == 10

    assert settings.ACCESS_TOKEN_EXPIRE_DAYS == 7
    assert settings.ACCESS_TOKEN_ALGORITHM == "HS256"  # noqa: S105

    # User
    assert settings.USER_LINK_LIMIT == 100

    # API
    assert settings.API_VERSION_PREFIX == "/v1"
    assert settings.AUTH_PREFIX == "/auth"
    assert settings.LINKS_PREFIX == "/links"
    assert settings.FORWARD_PREFIX == "/forward"

    # SMTP
    assert settings.FROM_EMAIL == "hello@lnkr.by"
