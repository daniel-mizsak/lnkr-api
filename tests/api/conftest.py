"""
Fixtures used in testing the api.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

import os
from collections.abc import AsyncGenerator, Callable, Generator, Iterator

import pytest
from fakeredis import FakeAsyncRedis
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from testcontainers.postgres import PostgresContainer

from lnkr.api.dependencies import get_cache, get_current_user, get_session
from lnkr.main import app
from lnkr.models import User
from lnkr.models.base import Base


# TODO: Use `async` API calls in tests.
@pytest.fixture(name="engine", scope="session")
async def engine_fixture() -> AsyncGenerator[AsyncEngine]:
    with PostgresContainer(str(os.getenv("POSTGRES_IMAGE")), driver="psycopg") as container:
        engine = create_async_engine(container.get_connection_url())
        try:
            yield engine
        finally:
            await engine.dispose()


@pytest.fixture(name="session")
async def session_fixture(engine: AsyncEngine, user: User, other_user: User) -> AsyncGenerator[AsyncSession]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        session.add_all([user, other_user])
        await session.commit()
        yield session


@pytest.fixture(name="client")
def client_fixture(session: AsyncSession, user: User) -> Iterator[TestClient]:
    fake_async_redis = FakeAsyncRedis(decode_responses=True)

    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_cache] = lambda: fake_async_redis

    client = TestClient(app)
    try:
        yield client
    finally:
        client.close()
        app.dependency_overrides.clear()


OverrideUserFunction = Callable[[User], None]
OverrideUserFixture = Generator[OverrideUserFunction]


@pytest.fixture()
def override_current_user() -> OverrideUserFixture:
    original_user = app.dependency_overrides.get(get_current_user)

    def _override(user: User) -> None:
        app.dependency_overrides[get_current_user] = lambda: user

    yield _override

    if original_user is not None:
        app.dependency_overrides[get_current_user] = original_user
