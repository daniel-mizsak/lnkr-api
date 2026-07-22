"""
Tests for the request login token endpoint.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING
from unittest import mock

import pytest
from bs4 import BeautifulSoup
from fastapi import status
from sqlalchemy import select

from lnkr.api.dependencies.header import CLIENT_IP_HEADER, USER_AGENT_HEADER
from lnkr.api.routes import auth_route
from lnkr.config.application_settings import application_settings
from lnkr.exceptions import LoginTokenGenerationError
from lnkr.models import LoginToken

if TYPE_CHECKING:
    from httpx2 import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.usefixtures("override_verify_frontend_api_key")
async def test_request_login_token__missing_frontend_api_key(client: AsyncClient) -> None:
    response = await client.post(
        url=f"{application_settings.AUTH_PREFIX}/request-login-token",
    )
    data = response.json()

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    error = data["detail"][0]
    assert error["msg"] == "The provided frontend api key is invalid"
    assert error["type"] == "frontend_api_key_invalid"


async def test_request_login_token__login_token_generation_failure(
    client: AsyncClient,
    mock_send_email: mock.AsyncMock,
    email: str,
) -> None:
    create_login_token = mock.AsyncMock(side_effect=LoginTokenGenerationError())
    with mock.patch.object(auth_route, "create_and_save_login_token", create_login_token):
        response = await client.post(
            url=f"{application_settings.AUTH_PREFIX}/request-login-token",
            json={"email": email},
        )

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    error = response.json()["detail"][0]
    assert error["msg"] == "Unable to generate a login token. Please try again."
    assert error["type"] == "login_token_generation_failed"
    create_login_token.assert_awaited_once()
    mock_send_email.assert_not_awaited()


async def test_request_login_token__missing_request_metadata(
    client: AsyncClient,
    mock_send_email: mock.AsyncMock,
    email: str,
    user_agent_unrecognized: str,
) -> None:
    response = await client.post(
        url=f"{application_settings.AUTH_PREFIX}/request-login-token",
        json={"email": email},
        headers={USER_AGENT_HEADER: user_agent_unrecognized},
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    mock_send_email.assert_awaited_once()

    await_args = mock_send_email.await_args
    assert await_args is not None
    sent_email = await_args.args[0]
    email_body = sent_email.get_payload()[0].get_payload(decode=True).decode()
    soup = BeautifulSoup(email_body, "html.parser")

    assert _get_text_by_class(soup, "request-ip-address") == "Unavailable"
    assert _get_text_by_class(soup, "request-country-code") == "Unavailable"
    assert _get_text_by_class(soup, "request-user-agent") == "Unavailable"


async def test_request_login_token__complete_request_metadata(
    client: AsyncClient,
    session: AsyncSession,
    mock_send_email: mock.AsyncMock,
    email: str,
    ip_address_public: str,
    ip_address_public_country_code: str,
    user_agent: str,
) -> None:
    response = await client.post(
        url=f"{application_settings.AUTH_PREFIX}/request-login-token",
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
