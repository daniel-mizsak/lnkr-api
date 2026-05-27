"""
General fixtures.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from datetime import UTC, datetime, timedelta

import pytest

from lnkr.models import User


@pytest.fixture(name="email")
def email_fixture() -> str:
    return "user@example.com"


@pytest.fixture(name="user")
def user_fixture(email: str) -> User:
    return User(email=email)


@pytest.fixture(name="other_user")
def other_user_fixture(email: str) -> User:
    return User(email=f"other_{email}")


@pytest.fixture(name="slug")
def slug_fixture() -> str:
    return "slug"


@pytest.fixture(name="target_url")
def target_url_fixture() -> str:
    return "https://example.com/"


@pytest.fixture(name="target_url_invalid")
def target_url_invalid_fixture() -> str:
    return "example.com/"


@pytest.fixture(name="password")
def password_fixture() -> str:
    return "password"


@pytest.fixture(name="future_expires_at")
def future_expires_at_fixture() -> datetime:
    return datetime.now(UTC) + timedelta(days=1)


@pytest.fixture(name="past_expires_at")
def past_expires_at_fixture() -> datetime:
    return datetime.now(UTC) - timedelta(days=1)
