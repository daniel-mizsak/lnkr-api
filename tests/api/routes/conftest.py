"""
Fixtures used in testing API routes.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

from collections.abc import AsyncIterator, Awaitable, Callable, Generator
from typing import TYPE_CHECKING
from unittest import mock

import pytest
from bs4 import BeautifulSoup
from fakeredis import FakeAsyncRedis
from fastapi import status
from httpx2 import ASGITransport, AsyncClient

from lnkr.api.dependencies import (
    get_cache,
    get_current_user,
    get_geoip_reader,
    get_session,
    verify_frontend_api_key,
)
from lnkr.api.routes import auth_route
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
def geoip_database_unavailable(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> Generator[None]:  # noqa: ARG001
    # Use the real dependency to read None from application state, covering both the dependency and endpoint.
    monkeypatch.setattr(app.state, "geoip_reader", None, raising=False)
    original_reader = app.dependency_overrides.pop(get_geoip_reader)
    try:
        yield
    finally:
        app.dependency_overrides[get_geoip_reader] = original_reader


@pytest.fixture()
def override_authentication(client: AsyncClient) -> Generator[None]:  # noqa: ARG001
    original_user = app.dependency_overrides.pop(get_current_user)

    try:
        yield
    finally:
        app.dependency_overrides[get_current_user] = original_user


@pytest.fixture()
def override_get_current_user(client: AsyncClient) -> OverrideGetCurrentUserFixture:  # noqa: ARG001
    original_user = app.dependency_overrides[get_current_user]

    def _override(user: User) -> None:
        app.dependency_overrides[get_current_user] = lambda: user

    try:
        yield _override
    finally:
        app.dependency_overrides[get_current_user] = original_user


RequestLoginTokenFunction = Callable[[str], Awaitable[str]]
IssueAuthTokensFunction = Callable[[str], Awaitable[dict[str, str]]]


@pytest.fixture(name="mock_send_email")
def mock_send_email_fixture() -> Generator[mock.AsyncMock]:
    mock_send_email = mock.AsyncMock()
    with mock.patch.object(auth_route, "send_email", mock_send_email):
        yield mock_send_email


@pytest.fixture(name="request_login_token")
def request_login_token_fixture(client: AsyncClient, mock_send_email: mock.AsyncMock) -> RequestLoginTokenFunction:
    async def request_login_token(email: str) -> str:
        await client.post(
            url=f"{application_settings.AUTH_PREFIX}/request-login-token",
            json={"email": email},
        )
        await_args = mock_send_email.await_args
        assert await_args is not None
        sent_email = await_args.args[0]
        email_body = sent_email.get_payload()[0].get_payload(decode=True).decode()
        soup = BeautifulSoup(email_body, "html.parser")
        login_token_element = soup.find(class_="login-token")
        assert login_token_element is not None
        return login_token_element.get_text()

    return request_login_token


@pytest.fixture(name="issue_auth_tokens")
def issue_auth_tokens_fixture(
    client: AsyncClient,
    request_login_token: RequestLoginTokenFunction,
) -> IssueAuthTokensFunction:
    async def issue_auth_tokens(email: str) -> dict[str, str]:
        login_token = await request_login_token(email)
        response = await client.post(
            url=f"{application_settings.AUTH_PREFIX}/verify-login-token",
            json={"login_token_value": login_token},
        )
        assert response.status_code == status.HTTP_200_OK
        return response.json()

    return issue_auth_tokens


@pytest.fixture(name="requested_login_token")
async def requested_login_token_fixture(
    request_login_token: RequestLoginTokenFunction,
    email: str,
    frozen_now: None,  # noqa: ARG001
) -> str:
    return await request_login_token(email)


@pytest.fixture(name="issued_auth_tokens")
async def issued_auth_tokens_fixture(
    issue_auth_tokens: IssueAuthTokensFunction,
    email: str,
    frozen_now: None,  # noqa: ARG001
) -> dict[str, str]:
    return await issue_auth_tokens(email)
