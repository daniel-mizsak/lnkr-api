"""
Tests for the request login token endpoint.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest
from bs4 import BeautifulSoup
from fastapi import status

from lnkr.config import settings
from lnkr.services.access_token_service import decode_access_token

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


@pytest.fixture(name="mock_send_email")
def mock_send_email_fixture(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    mock_send_email = AsyncMock()
    monkeypatch.setattr("lnkr.api.routes.auth_route.send_email", mock_send_email)
    return mock_send_email


def test_request_login_token__success(client: TestClient, mock_send_email: AsyncMock, email: str) -> None:
    response = client.post(
        url=f"{settings.API_VERSION_PREFIX}{settings.AUTH_PREFIX}/request-login-token",
        json={"email": email},
    )
    assert response.status_code == status.HTTP_200_OK

    mock_send_email.assert_awaited_once()

    await_args = mock_send_email.await_args
    assert await_args is not None
    sent_email = await_args.args[0]

    assert sent_email["To"] == email
    assert sent_email["From"] == settings.FROM_EMAIL
    assert sent_email["Subject"] == "Email Verification - lnkr"

    email_body = sent_email.get_payload()[0].get_payload(decode=True).decode()
    soup = BeautifulSoup(email_body, "html.parser")
    login_token_span = soup.find("span", class_="login-token")
    assert login_token_span is not None
    login_token_value = login_token_span.get_text().strip()

    # Call the verify_login_token endpoint to ensure the token is valid.
    response = client.get(
        url=f"{settings.API_VERSION_PREFIX}{settings.AUTH_PREFIX}/verify-login-token",
        params={"login_token_value": login_token_value},
    )
    data = response.json()
    access_token_payload = decode_access_token(data["access_token"])

    assert response.status_code == status.HTTP_200_OK
    assert access_token_payload.sub == email
