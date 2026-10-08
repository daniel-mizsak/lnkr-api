"""
Tests for the revoke refresh token endpoint.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

import logging
from typing import TYPE_CHECKING

import pytest
from fastapi import status

from lnkr.api.routes import auth_route
from lnkr.config.application_settings import application_settings

if TYPE_CHECKING:
    from httpx2 import AsyncClient


@pytest.mark.usefixtures("override_verify_frontend_api_key")
async def test_revoke_refresh_token__missing_frontend_api_key(client: AsyncClient) -> None:
    response = await client.post(url=f"{application_settings.AUTH_PREFIX}/revoke-refresh-token")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    data = response.json()
    error = data["detail"][0]

    assert error["msg"] == "The provided frontend api key is invalid"
    assert error["type"] == "frontend_api_key_invalid"


async def test_revoke_refresh_token__invalid_refresh_token(
    client: AsyncClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger=auth_route.__name__)

    response = await client.post(
        url=f"{application_settings.AUTH_PREFIX}/revoke-refresh-token",
        json={"refresh_token_value": ""},
    )
    records = [record for record in caplog.records if record.name == auth_route.__name__]

    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    data = response.json()
    error = data["detail"][0]

    assert error["msg"] == "The provided refresh token is invalid, used, revoked or has expired"
    assert error["type"] == "refresh_token_invalid"
    assert [(record.levelno, record.getMessage()) for record in records] == [
        (logging.INFO, "auth.revoke_token_invalid")
    ]


async def test_revoke_refresh_token__valid_refresh_token(
    client: AsyncClient,
    issued_auth_tokens: dict[str, str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger=auth_route.__name__)
    refresh_token_value = issued_auth_tokens["refresh_token"]

    response = await client.post(
        url=f"{application_settings.AUTH_PREFIX}/revoke-refresh-token",
        json={"refresh_token_value": refresh_token_value},
    )
    records = [record for record in caplog.records if record.name == auth_route.__name__]

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert [(record.levelno, record.getMessage()) for record in records] == [(logging.INFO, "auth.revoke_succeeded")]
