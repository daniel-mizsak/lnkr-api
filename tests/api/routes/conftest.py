"""
Fixtures used in testing API routes.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from collections.abc import AsyncIterator, Callable, Generator
from typing import TYPE_CHECKING

import pytest
from fakeredis import FakeAsyncRedis
from httpx2 import ASGITransport, AsyncClient

from lnkr.api.dependencies import (
    get_cache,
    get_current_user,
    get_geoip_reader,
    get_session,
    verify_frontend_api_key,
)
from lnkr.config.application_settings import application_settings
from lnkr.main import app
from lnkr.models import User

if TYPE_CHECKING:
    from geoip2.database import Reader
    from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture(name="client")
async def client_fixture(session: AsyncSession, user: User, geoip_reader: Reader) -> AsyncIterator[AsyncClient]:
    fake_async_redis = FakeAsyncRedis(decode_responses=True)

    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_cache] = lambda: fake_async_redis
    app.dependency_overrides[get_geoip_reader] = lambda: geoip_reader
    app.dependency_overrides[verify_frontend_api_key] = lambda: None
    transport = ASGITransport(app=app)
    try:
        # Match Starlette TestClient's default base_url: "http://testserver".
        base_url = f"http://testserver{application_settings.API_VERSION_PREFIX}"
        async with AsyncClient(transport=transport, base_url=base_url) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        await fake_async_redis.aclose()


OverrideGetCurrentUserFunction = Callable[[User], None]
OverrideGetCurrentUserFixture = Generator[OverrideGetCurrentUserFunction]


@pytest.fixture()
def override_get_current_user(client: AsyncClient) -> OverrideGetCurrentUserFixture:  # noqa: ARG001
    original_user = app.dependency_overrides[get_current_user]

    def _override(user: User) -> None:
        app.dependency_overrides[get_current_user] = lambda: user

    try:
        yield _override
    finally:
        app.dependency_overrides[get_current_user] = original_user
