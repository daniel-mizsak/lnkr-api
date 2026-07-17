"""
Fixtures used in testing the api.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from collections.abc import Callable, Generator, Iterator
from typing import TYPE_CHECKING

import pytest
from fakeredis import FakeAsyncRedis
from fastapi.testclient import TestClient

from lnkr.api.dependencies import (
    get_cache,
    get_current_user,
    get_geoip_reader,
    get_session,
    verify_frontend_api_key,
)
from lnkr.main import app
from lnkr.models import User

if TYPE_CHECKING:
    from geoip2.database import Reader
    from sqlalchemy.ext.asyncio import AsyncSession


# TODO: Use `async` API calls in tests.
@pytest.fixture(name="client")
def client_fixture(session: AsyncSession, user: User, geoip_reader: Reader) -> Iterator[TestClient]:
    fake_async_redis = FakeAsyncRedis(decode_responses=True)

    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_cache] = lambda: fake_async_redis
    app.dependency_overrides[get_geoip_reader] = lambda: geoip_reader
    app.dependency_overrides[verify_frontend_api_key] = lambda: None
    client = TestClient(app)
    try:
        yield client
    finally:
        client.close()
        app.dependency_overrides.clear()


OverrideGetCurrentUserFunction = Callable[[User], None]
OverrideGetCurrentUserFixture = Generator[OverrideGetCurrentUserFunction]


@pytest.fixture()
def override_get_current_user() -> OverrideGetCurrentUserFixture:
    original_user = app.dependency_overrides.get(get_current_user)

    def _override(user: User) -> None:
        app.dependency_overrides[get_current_user] = lambda: user

    yield _override
    if original_user is not None:
        app.dependency_overrides[get_current_user] = original_user
