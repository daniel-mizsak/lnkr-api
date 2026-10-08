"""
Tests for the verify login token endpoint.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

import logging
from typing import TYPE_CHECKING
from unittest import mock

import pytest
from fastapi import status

from lnkr.api.routes import auth_route
from lnkr.config.application_settings import application_settings
from lnkr.exceptions import RefreshTokenGenerationError
from lnkr.services.tokens.access_token_service import decode_access_token

if TYPE_CHECKING:
    from httpx2 import AsyncClient

    from lnkr.models import User


@pytest.mark.usefixtures("override_verify_frontend_api_key")
async def test_verify_login_token__missing_frontend_api_key(client: AsyncClient) -> None:
    response = await client.post(
        url=f"{application_settings.AUTH_PREFIX}/verify-login-token",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    data = response.json()
    error = data["detail"][0]

    assert error["msg"] == "The provided frontend api key is invalid"
    assert error["type"] == "frontend_api_key_invalid"


async def test_verify_login_token__invalid_login_token(client: AsyncClient, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger=auth_route.__name__)

    response = await client.post(
        url=f"{application_settings.AUTH_PREFIX}/verify-login-token",
        json={"login_token_value": ""},
    )
    records = [record for record in caplog.records if record.name == auth_route.__name__]

    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    data = response.json()
    error = data["detail"][0]

    assert error["msg"] == "The provided login token is invalid, used or has expired"
    assert error["type"] == "login_token_invalid"
    assert [(record.levelno, record.getMessage()) for record in records] == [(logging.INFO, "auth.login_token_invalid")]


async def test_verify_login_token__refresh_token_generation_failure(
    client: AsyncClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger=auth_route.__name__)
    generation_error = RefreshTokenGenerationError()

    with mock.patch.object(
        auth_route,
        "authenticate_with_login_token",
        mock.AsyncMock(side_effect=generation_error),
    ):
        response = await client.post(
            url=f"{application_settings.AUTH_PREFIX}/verify-login-token",
            json={"login_token_value": "value"},
        )
    records = [record for record in caplog.records if record.name == auth_route.__name__]

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    data = response.json()
    error = data["detail"][0]

    assert error["msg"] == "Unable to generate a refresh token. Please try again."
    assert error["type"] == "refresh_token_generation_failed"
    assert [(record.levelno, record.getMessage()) for record in records] == [
        (logging.ERROR, "auth.refresh_token_retries_exhausted")
    ]
    assert records[0].exc_info is not None
    assert records[0].exc_info[1] is generation_error


async def test_verify_login_token__valid_login_token(
    client: AsyncClient,
    requested_login_token: str,
    user: User,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger=auth_route.__name__)

    response = await client.post(
        url=f"{application_settings.AUTH_PREFIX}/verify-login-token",
        json={"login_token_value": requested_login_token},
    )
    records = [record for record in caplog.records if record.name == auth_route.__name__]

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    access_token_payload = decode_access_token(data["access_token"])

    assert set(data.keys()) == {"access_token", "refresh_token", "token_type"}
    assert access_token_payload.sub == str(user.id)
    assert access_token_payload.type == "access"
    assert data["refresh_token"]
    assert data["token_type"] == "bearer"  # noqa: S105
    assert [(record.levelno, record.getMessage()) for record in records] == [(logging.INFO, "auth.login_succeeded")]
