"""
Fixtures used in testing auth api routes.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING
from unittest import mock

import pytest
from bs4 import BeautifulSoup
from fastapi import status

from lnkr.api.dependencies import verify_frontend_api_key
from lnkr.api.routes import auth_route
from lnkr.config.application_settings import application_settings
from lnkr.main import app

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator

    from httpx2 import AsyncClient


@pytest.fixture(name="mock_send_email")
def mock_send_email_fixture() -> Generator[mock.AsyncMock]:
    mock_send_email = mock.AsyncMock()
    with mock.patch.object(auth_route, "send_email", mock_send_email):
        yield mock_send_email


@pytest.fixture(name="issued_login_token")
async def issued_login_token_fixture(client: AsyncClient, mock_send_email: mock.AsyncMock, email: str) -> str:
    await client.post(
        url=f"{application_settings.AUTH_PREFIX}/request-login-token",
        json={"email": email},
    )

    await_args = mock_send_email.await_args
    assert await_args is not None
    sent_email = await_args.args[0]

    email_body = sent_email.get_payload()[0].get_payload(decode=True).decode()
    soup = BeautifulSoup(email_body, "html.parser")
    login_token_span = soup.find("span", class_="login-token")
    assert login_token_span is not None
    return login_token_span.get_text().strip()


@pytest.fixture(name="issued_auth_tokens")
async def issued_auth_tokens_fixture(client: AsyncClient, issued_login_token: str) -> dict[str, str]:
    response = await client.post(
        url=f"{application_settings.AUTH_PREFIX}/verify-login-token",
        json={"login_token_value": issued_login_token},
    )
    assert response.status_code == status.HTTP_200_OK
    return response.json()


@pytest.fixture()
async def override_verify_frontend_api_key(client: AsyncClient) -> AsyncGenerator[None]:  # noqa: ARG001
    # Depend on `client` so this fixture runs after the default override is installed,
    # then pop it so the real dependency runs and raises on the missing header.
    original_frontend_api_key = app.dependency_overrides.pop(verify_frontend_api_key, None)
    yield
    if original_frontend_api_key is not None:
        app.dependency_overrides[verify_frontend_api_key] = original_frontend_api_key
