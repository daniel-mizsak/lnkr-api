"""
Tests for the request login token endpoint.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING

import pytest
from bs4 import BeautifulSoup
from fastapi import status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from lnkr.api.dependencies.header import CLIENT_IP_HEADER, USER_AGENT_HEADER
from lnkr.config.application_settings import application_settings
from lnkr.database.tokens import login_token_database
from lnkr.models import LoginToken

if TYPE_CHECKING:
    from unittest.mock import AsyncMock

    from fastapi.testclient import TestClient
    from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.usefixtures("override_verify_frontend_api_key")
def test_request_login_token__missing_frontend_api_key(client: TestClient) -> None:
    response = client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.AUTH_PREFIX}/request-login-token",
    )
    data = response.json()

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    error = data["detail"][0]
    assert error["msg"] == "The provided frontend api key is invalid"
    assert error["type"] == "frontend_api_key_invalid"


def test_request_login_token__login_token_generation_attempts_exhausted(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    mock_send_email: AsyncMock,
    email: str,
) -> None:
    # Raise IntegrityError to simulate a hash collision, which will exhaust the login token generation attempts.
    async def _save_login_token(_session: AsyncSession, _login_token: object) -> object:
        raise IntegrityError(statement=None, params=None, orig=Exception("token hash collision"))

    monkeypatch.setattr(login_token_database, "save_login_token", _save_login_token)

    response = client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.AUTH_PREFIX}/request-login-token",
        json={"email": email},
    )
    data = response.json()

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    mock_send_email.assert_not_awaited()
    error = data["detail"][0]
    assert error["msg"] == "Unable to generate a login token. Please try again."
    assert error["type"] == "login_token_generation_failed"


def test_request_login_token__missing_metadata(
    client: TestClient,
    mock_send_email: AsyncMock,
    email: str,
    user_agent_unrecognized: str,
) -> None:
    response = client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.AUTH_PREFIX}/request-login-token",
        json={"email": email},
        headers={USER_AGENT_HEADER: user_agent_unrecognized},
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT

    await_args = mock_send_email.await_args
    assert await_args is not None
    sent_email = await_args.args[0]
    email_body = sent_email.get_payload()[0].get_payload(decode=True).decode()
    soup = BeautifulSoup(email_body, "html.parser")

    assert _get_text_by_class(soup, "request-ip-address") == "Unavailable"
    assert _get_text_by_class(soup, "request-country-code") == "Unavailable"
    assert _get_text_by_class(soup, "request-user-agent") == "Unavailable"


async def test_request_login_token__success(
    client: TestClient,
    session: AsyncSession,
    mock_send_email: AsyncMock,
    email: str,
    ip_address_public: str,
    ip_address_public_country_code: str,
    user_agent: str,
) -> None:
    response = client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.AUTH_PREFIX}/request-login-token",
        json={"email": email},
        headers={CLIENT_IP_HEADER: ip_address_public, USER_AGENT_HEADER: user_agent},
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT

    mock_send_email.assert_awaited_once()

    await_args = mock_send_email.await_args
    assert await_args is not None
    sent_email = await_args.args[0]

    assert sent_email["To"] == email
    assert sent_email["From"] == application_settings.FROM_EMAIL
    assert sent_email["Subject"] == "Email Verification - lnkr"

    email_body = sent_email.get_payload()[0].get_payload(decode=True).decode()
    soup = BeautifulSoup(email_body, "html.parser")
    login_token_value = _get_text_by_class(soup, "login-token")
    assert len(login_token_value) == 6
    assert _get_text_by_class(soup, "request-ip-address") == ip_address_public
    assert _get_text_by_class(soup, "request-country-code") == ip_address_public_country_code
    assert _get_text_by_class(soup, "request-user-agent") == "Chrome on Mac OS X"

    result = await session.execute(select(LoginToken))
    login_token = result.scalar_one()
    assert login_token.ip_address == ip_address_public
    assert login_token.country_code == ip_address_public_country_code
    assert login_token.browser == "Chrome"
    assert login_token.operating_system == "Mac OS X"


def _get_text_by_class(soup: BeautifulSoup, class_name: str) -> str:
    element = soup.find(class_=class_name)
    assert element is not None
    return element.get_text(strip=True)
