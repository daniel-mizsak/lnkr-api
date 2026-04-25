"""
Fixtures used in testing auth api routes.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest
from bs4 import BeautifulSoup
from fastapi import status

from lnkr.config.application_settings import application_settings

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


@pytest.fixture(name="mock_send_email")
def mock_send_email_fixture(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    mock_send_email = AsyncMock()
    monkeypatch.setattr("lnkr.api.routes.auth_route.send_email", mock_send_email)
    return mock_send_email


@pytest.fixture(name="issued_login_token")
def issued_login_token_fixture(client: TestClient, mock_send_email: AsyncMock, email: str) -> str:
    client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.AUTH_PREFIX}/request-login-token",
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
def issued_auth_tokens_fixture(client: TestClient, issued_login_token: str) -> dict[str, str]:
    response = client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.AUTH_PREFIX}/verify-login-token",
        json={"login_token_value": issued_login_token},
    )
    assert response.status_code == status.HTTP_200_OK
    return response.json()
