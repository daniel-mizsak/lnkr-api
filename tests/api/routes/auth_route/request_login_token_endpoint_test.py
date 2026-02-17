"""
Tests for the request login token endpoint.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

from typing import TYPE_CHECKING

from bs4 import BeautifulSoup
from fastapi import status

from lnkr.config import settings
from lnkr.services.access_token_service import decode_access_token

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from fastapi.testclient import TestClient


def test_request_login_token__success(client: TestClient, mock_smtp: MagicMock, email: str) -> None:
    response = client.post(
        url=f"{settings.API_VERSION_PREFIX}{settings.AUTH_PREFIX}/request-login-token",
        json={"email": email},
    )
    assert response.status_code == status.HTTP_200_OK

    mock_smtp.send_message.assert_called_once()
    sent_email = mock_smtp.send_message.call_args[0][0]

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
