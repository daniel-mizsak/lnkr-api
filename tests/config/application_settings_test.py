"""
Tests for the lnkr configurations.

These tests ensure that changes to the default configurations will break the tests.
Otherwise, (since the api tests are using references to the default values) the tests
will pass in case of an accidental change.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from lnkr.config.application_settings import ApplicationEnvironment, application_settings


def test_application_environment() -> None:
    assert set(ApplicationEnvironment.__members__.keys()) == {"DEVELOPMENT", "PRODUCTION"}

    assert ApplicationEnvironment.DEVELOPMENT.value == "development"
    assert ApplicationEnvironment.PRODUCTION.value == "production"


def test_application_settings() -> None:
    # General
    assert application_settings.ENVIRONMENT == ApplicationEnvironment.DEVELOPMENT
    assert application_settings.FRONTEND_APP_URL == "https://app.lnkr.by"
    assert application_settings.FRONTEND_FORWARD_URL == "https://lnkr.by"
    assert application_settings.DEVELOPMENT_USER_EMAIL == "user@example.com"

    assert application_settings.LOGIN_TOKEN_EXPIRE_MINUTES == 10
    assert application_settings.REFRESH_TOKEN_EXPIRE_DAYS == 7
    assert application_settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30
    assert application_settings.ACCESS_TOKEN_ALGORITHM == "HS256"  # noqa: S105

    assert application_settings.LINK_CACHE_TTL_SECONDS == 60 * 60 * 24  # 24 hours

    # User
    assert application_settings.USER_LINK_LIMIT == 100

    # API
    assert application_settings.API_VERSION == "v1"
    assert application_settings.API_VERSION_PREFIX == "/v1"
    assert application_settings.AUTH_PREFIX == "/auth"
    assert application_settings.FORWARD_PREFIX == "/forward"
    assert application_settings.LINKS_PREFIX == "/links"
    assert application_settings.USER_PREFIX == "/user"

    # SMTP
    assert application_settings.FROM_EMAIL == "hello@lnkr.by"
