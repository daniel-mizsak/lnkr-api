"""
Fixtures used in testing the api.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

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


@pytest.fixture(name="target_url")
def target_url_fixture() -> str:
    return "https://example.com/"


@pytest.fixture(name="target_url_invalid")
def target_url_invalid_fixture() -> str:
    return "example.com/"


@pytest.fixture(name="slug")
def slug_fixture() -> str:
    return "slug"
