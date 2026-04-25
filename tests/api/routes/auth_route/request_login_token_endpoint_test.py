"""
Tests for the request login token endpoint.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING

from bs4 import BeautifulSoup
from fastapi import status

from lnkr.config.application_settings import application_settings

if TYPE_CHECKING:
    from unittest.mock import AsyncMock

    from fastapi.testclient import TestClient


def test_request_login_token__success(client: TestClient, mock_send_email: AsyncMock, email: str) -> None:
    response = client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.AUTH_PREFIX}/request-login-token",
        json={"email": email},
    )
    assert response.status_code == status.HTTP_200_OK

    mock_send_email.assert_awaited_once()

    await_args = mock_send_email.await_args
    assert await_args is not None
    sent_email = await_args.args[0]

    assert sent_email["To"] == email
    assert sent_email["From"] == application_settings.FROM_EMAIL
    assert sent_email["Subject"] == "Email Verification - lnkr"

    email_body = sent_email.get_payload()[0].get_payload(decode=True).decode()
    soup = BeautifulSoup(email_body, "html.parser")
    login_token_span = soup.find("span", class_="login-token")
    assert login_token_span is not None
    login_token_value = login_token_span.get_text().strip()
    assert len(login_token_value) == 6
