"""
Fixtures used in testing api routes.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

import smtplib
from collections.abc import AsyncGenerator, Callable, Generator, Iterator
from unittest.mock import MagicMock

import pytest
from fakeredis import FakeRedis
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from lnkr.api.dependencies import get_cache, get_current_user, get_session, get_smtp_server
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


@pytest.fixture(name="mock_smtp")
def mock_smtp_fixture() -> MagicMock:
    return MagicMock(spec=smtplib.SMTP)


@pytest.fixture(name="client")
def client_fixture(session: AsyncSession, mock_smtp: MagicMock, user: User) -> Iterator[TestClient]:
    fake_redis = FakeRedis()

    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_cache] = lambda: fake_redis
    app.dependency_overrides[get_smtp_server] = lambda: mock_smtp

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
