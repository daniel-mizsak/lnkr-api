"""
Fixtures used in testing api routes.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

from collections.abc import AsyncGenerator, Callable, Generator, Iterator

import pytest
from fakeredis import FakeAsyncRedis
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from lnkr.api.dependencies import get_cache, get_current_user, get_session
from lnkr.main import app
from lnkr.models import User
from lnkr.models.base import Base


@pytest.fixture(name="session")
async def session_fixture(user: User, other_user: User) -> AsyncGenerator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSession(engine, expire_on_commit=False) as session:
        session.add(user)
        session.add(other_user)
        await session.commit()
        yield session
    await engine.dispose()


@pytest.fixture(name="client")
def client_fixture(session: AsyncSession, user: User) -> Iterator[TestClient]:
    fake_async_redis = FakeAsyncRedis()

    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_cache] = lambda: fake_async_redis

    client = TestClient(app)
    yield client
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
