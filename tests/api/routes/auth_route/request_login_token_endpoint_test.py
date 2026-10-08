"""
Tests for the request login token endpoint.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

import logging
import smtplib
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

    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    data = response.json()
    error = data["detail"][0]

    assert error["msg"] == "The provided frontend api key is invalid"
    assert error["type"] == "frontend_api_key_invalid"


async def test_request_login_token__login_token_generation_failure(
    client: AsyncClient,
    mock_send_email: mock.AsyncMock,
    email: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger=auth_route.__name__)
    generation_error = LoginTokenGenerationError()
    create_and_save_login_token = mock.AsyncMock(side_effect=generation_error)

    with mock.patch.object(auth_route, "create_and_save_login_token", create_and_save_login_token):
        response = await client.post(
            url=f"{application_settings.AUTH_PREFIX}/request-login-token",
            json={"email": email},
        )
    records = [record for record in caplog.records if record.name == auth_route.__name__]

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    data = response.json()
    error = data["detail"][0]

    assert error["msg"] == "Unable to generate a login token. Please try again."
    assert error["type"] == "login_token_generation_failed"
    create_and_save_login_token.assert_awaited_once()
    mock_send_email.assert_not_awaited()
    assert [(record.levelno, record.getMessage()) for record in records] == [
        (logging.ERROR, "auth.login_token_retries_exhausted")
    ]
    assert records[0].exc_info is not None
    assert records[0].exc_info[1] is generation_error


@pytest.mark.usefixtures("frozen_now")
@pytest.mark.parametrize(
    "send_error",
    [
        pytest.param(smtplib.SMTPDataError(550, b"Private provider details"), id="smtp-failure"),
        pytest.param(TimeoutError("Private connection details"), id="timeout"),
        pytest.param(OSError("Private OS details"), id="os-failure"),
    ],
)
async def test_request_login_token__email_delivery_failure(
    client: AsyncClient,
    mock_send_email: mock.AsyncMock,
    email: str,
    send_error: OSError,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger=auth_route.__name__)
    mock_send_email.side_effect = send_error

    response = await client.post(
        url=f"{application_settings.AUTH_PREFIX}/request-login-token",
        json={"email": email},
    )
    records = [record for record in caplog.records if record.name == auth_route.__name__]

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.headers["retry-after"] == "60"
    assert response.headers["cache-control"] == "no-store"

    data = response.json()
    error = data["detail"][0]

    assert error["msg"] == "Unable to send a login token. Please request a new token in 60 seconds."
    assert error["type"] == "login_token_delivery_failed"
    assert records == []


@pytest.mark.usefixtures("frozen_now")
async def test_request_login_token__successful_request_after_email_delivery_failure(
    client: AsyncClient,
    mock_send_email: mock.AsyncMock,
    email: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger=auth_route.__name__)
    mock_send_email.side_effect = [TimeoutError("Timed out"), None]

    failed_response = await client.post(
        url=f"{application_settings.AUTH_PREFIX}/request-login-token",
        json={"email": email},
    )
    retry_response = await client.post(
        url=f"{application_settings.AUTH_PREFIX}/request-login-token",
        json={"email": email},
    )
    records = [record for record in caplog.records if record.name == auth_route.__name__]

    assert failed_response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert retry_response.status_code == status.HTTP_204_NO_CONTENT
    assert retry_response.content == b""

    failed_call = mock_send_email.await_args_list[0]
    failed_message = failed_call.args[0]
    failed_idempotency_key = failed_message["Resend-Idempotency-Key"]
    retry_call = mock_send_email.await_args_list[1]
    retry_message = retry_call.args[0]
    retry_idempotency_key = retry_message["Resend-Idempotency-Key"]

    assert failed_idempotency_key
    assert retry_idempotency_key
    assert retry_idempotency_key != failed_idempotency_key
    assert [(record.levelno, record.getMessage()) for record in records] == [
        (logging.INFO, "auth.login_token_requested")
    ]


async def test_request_login_token__missing_request_metadata(
    client: AsyncClient,
    mock_send_email: mock.AsyncMock,
    email: str,
    user_agent_unrecognized: str,
) -> None:
    await client.post(
        url=f"{application_settings.AUTH_PREFIX}/request-login-token",
        json={"email": email},
        headers={USER_AGENT_HEADER: user_agent_unrecognized},
    )

    mock_send_email.assert_awaited_once()

    await_args = mock_send_email.await_args
    assert await_args is not None
    sent_email = await_args.args[0]
    email_body = sent_email.get_payload()[0].get_payload(decode=True).decode()
    soup = BeautifulSoup(email_body, "html.parser")

    assert _get_text_by_class(soup, "request-ip-address") == "IP Not Found"
    assert _get_text_by_class(soup, "request-country-code") == "Country Not Found"
    assert soup.find(class_="request-country-flag") is None
    assert _get_text_by_class(soup, "request-operating-system") == "OS Not Found"
    assert _get_text_by_class(soup, "request-browser") == "Browser Not Found"


async def test_request_login_token__complete_request_metadata(
    client: AsyncClient,
    session: AsyncSession,
    mock_send_email: mock.AsyncMock,
    email: str,
    ip_address_public: str,
    ip_address_public_country_code: str,
    user_agent: str,
) -> None:
    await client.post(
        url=f"{application_settings.AUTH_PREFIX}/request-login-token",
        json={"email": email},
        headers={CLIENT_IP_HEADER: ip_address_public, USER_AGENT_HEADER: user_agent},
    )

    mock_send_email.assert_awaited_once()

    await_args = mock_send_email.await_args
    assert await_args is not None
    sent_email = await_args.args[0]

    assert sent_email["To"] == email
    assert sent_email["From"] == application_settings.FROM_EMAIL
    assert sent_email["Subject"] == "Sign in to lnkr.by"

    email_body = sent_email.get_payload()[0].get_payload(decode=True).decode()
    soup = BeautifulSoup(email_body, "html.parser")
    login_token_element = soup.find(class_="login-token")
    assert login_token_element is not None
    login_token_value = login_token_element.get_text()
    assert len(login_token_value) == 6
    assert _get_text_by_class(soup, "request-ip-address") == ip_address_public
    assert _get_text_by_class(soup, "request-country-code") == ip_address_public_country_code
    assert _get_text_by_class(soup, "request-country-flag") == "🇺🇸"
    assert _get_text_by_class(soup, "request-operating-system") == "Mac OS X"
    assert _get_text_by_class(soup, "request-browser") == "Chrome"

    result = await session.execute(select(LoginToken))
    login_token = result.scalar_one()
    assert login_token.ip_address == ip_address_public
    assert login_token.country_code == ip_address_public_country_code
    assert login_token.browser == "Chrome"
    assert login_token.operating_system == "Mac OS X"


@pytest.mark.usefixtures("geoip_database_unavailable")
async def test_request_login_token__geoip_database_unavailable(
    client: AsyncClient,
    session: AsyncSession,
    mock_send_email: mock.AsyncMock,
    email: str,
    ip_address_public: str,
) -> None:
    response = await client.post(
        url=f"{application_settings.AUTH_PREFIX}/request-login-token",
        json={"email": email},
        headers={CLIENT_IP_HEADER: ip_address_public},
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT

    mock_send_email.assert_awaited_once()

    await_args = mock_send_email.await_args
    assert await_args is not None
    sent_email = await_args.args[0]
    email_body = sent_email.get_payload()[0].get_payload(decode=True).decode()
    soup = BeautifulSoup(email_body, "html.parser")
    assert _get_text_by_class(soup, "request-ip-address") == ip_address_public
    assert _get_text_by_class(soup, "request-country-code") == "Country Not Found"
    assert soup.find(class_="request-country-flag") is None

    result = await session.execute(select(LoginToken))
    login_token = result.scalar_one()
    assert login_token.ip_address == ip_address_public
    assert login_token.country_code is None


def _get_text_by_class(soup: BeautifulSoup, class_name: str) -> str:
    element = soup.find(class_=class_name)
    assert element is not None
    return element.get_text(strip=True)
