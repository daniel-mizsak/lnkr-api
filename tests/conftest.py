"""
General fixtures.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

import ipaddress
import os
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import pytest
from geoip2.errors import AddressNotFoundError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from testcontainers.postgres import PostgresContainer

from lnkr.config.application_settings import application_settings
from lnkr.models import User
from lnkr.models.base import Base

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from geoip2.database import Reader
    from sqlalchemy.ext.asyncio import AsyncEngine


@pytest.fixture(name="engine", scope="session")
async def engine_fixture() -> AsyncGenerator[AsyncEngine]:
    with PostgresContainer(str(os.getenv("POSTGRES_IMAGE")), driver="psycopg") as container:
        engine = create_async_engine(container.get_connection_url())
        try:
            yield engine
        finally:
            await engine.dispose()


@pytest.fixture(name="session")
async def session_fixture(engine: AsyncEngine, user: User, user_other: User) -> AsyncGenerator[AsyncSession]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        session.add_all([user, user_other])
        await session.commit()
        yield session


@pytest.fixture(name="email")
def email_fixture() -> str:
    return "user@example.com"


@pytest.fixture(name="user")
def user_fixture(email: str) -> User:
    return User(email=email)


@pytest.fixture(name="user_other")
def user_other_fixture(email: str) -> User:
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


@pytest.fixture(name="expires_at_future")
def expires_at_future_fixture() -> datetime:
    return datetime.now(UTC) + timedelta(days=1)


@pytest.fixture(name="expires_at_past")
def expires_at_past_fixture() -> datetime:
    return datetime.now(UTC) - timedelta(days=1)


@pytest.fixture(name="frontend_api_key")
def frontend_api_key_fixture() -> str:
    return application_settings.FRONTEND_API_KEY.get_secret_value()


@pytest.fixture(name="frontend_api_key_invalid")
def frontend_api_key_invalid_fixture() -> str:
    return "frontend-api-key-invalid"


@pytest.fixture(name="ip_address_public")
def ip_address_public_fixture() -> str:
    return "8.8.8.8"


@pytest.fixture(name="ip_address_private")
def ip_address_private_fixture() -> str:
    return "192.168.1.1"


@pytest.fixture(name="ip_address_malformed")
def ip_address_malformed_fixture() -> str:
    return "not-an-ip"


@pytest.fixture(name="ip_address_public_country_code")
def ip_address_public_country_code_fixture() -> str:
    return "US"


@pytest.fixture(name="user_agent")
def user_agent_fixture() -> str:
    return (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
    )


@pytest.fixture(name="user_agent_unrecognized")
def user_agent_unrecognized_fixture() -> str:
    return "test-client"


@pytest.fixture(name="geoip_reader")
def geoip_reader_fixture(ip_address_public: str, ip_address_public_country_code: str) -> Reader:
    return cast("Reader", FakeGeoipReader({ip_address_public: ip_address_public_country_code}))


class FakeGeoipReader:
    """Mock implementation of geoip2.database.Reader for testing purposes."""

    def __init__(self, country_code_by_ip: dict[str, str]) -> None:
        self._country_code_by_ip = country_code_by_ip

    def country(self, ip_address: str) -> SimpleNamespace:
        ipaddress.ip_address(ip_address)
        try:
            iso_code = self._country_code_by_ip[ip_address]
        except KeyError as error:
            message = f"The address {ip_address} is not in the database."
            raise AddressNotFoundError(message) from error
        # Mirror the shape geoip2 returns, which production reads as `response.country.iso_code`.
        return SimpleNamespace(country=SimpleNamespace(iso_code=iso_code))
