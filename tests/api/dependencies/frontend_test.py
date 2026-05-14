"""
Tests for the frontend dependencies.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

import pytest
from fastapi import HTTPException, status

from lnkr.api.dependencies.frontend import check_frontend_api_key, verify_frontend_api_key
from lnkr.config.application_settings import application_settings


@pytest.fixture(name="frontend_api_key")
def frontend_api_key_fixture() -> str:
    return application_settings.FRONTEND_API_KEY.get_secret_value()


@pytest.fixture(name="frontend_api_key_invalid")
def frontend_api_key_invalid_fixture() -> str:
    return "frontend-api-key-invalid"


async def test_check_frontend_api_key__missing() -> None:
    assert await check_frontend_api_key(None) is False


async def test_check_frontend_api_key__invalid(frontend_api_key_invalid: str) -> None:
    assert await check_frontend_api_key(frontend_api_key_invalid) is False


async def test_check_frontend_api_key__valid(frontend_api_key: str) -> None:
    assert await check_frontend_api_key(frontend_api_key) is True


async def test_verify_frontend_api_key__missing() -> None:
    with pytest.raises(HTTPException) as exc_info:
        await verify_frontend_api_key(None)

    error = exc_info.value
    assert error.status_code == status.HTTP_401_UNAUTHORIZED
    assert error.detail[0]["type"] == "frontend_api_key_invalid"  # ty: ignore[invalid-argument-type]


async def test_verify_frontend_api_key__invalid(frontend_api_key_invalid: str) -> None:
    with pytest.raises(HTTPException) as exc_info:
        await verify_frontend_api_key(frontend_api_key_invalid)

    error = exc_info.value
    assert error.status_code == status.HTTP_401_UNAUTHORIZED
    assert error.detail[0]["type"] == "frontend_api_key_invalid"  # ty: ignore[invalid-argument-type]


async def test_verify_frontend_api_key__valid(frontend_api_key: str) -> None:
    assert await verify_frontend_api_key(frontend_api_key) is None
