"""
Tests for the header dependencies.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

import pytest
from fastapi import HTTPException, status

from lnkr.api.dependencies.header import (
    check_frontend_api_key,
    get_ip_address,
    get_user_agent,
    verify_frontend_api_key,
)
from lnkr.models.constraints import USER_AGENT_METADATA_MAX_LENGTH


def test_check_frontend_api_key__missing() -> None:
    assert check_frontend_api_key(None) is False


def test_check_frontend_api_key__invalid(frontend_api_key_invalid: str) -> None:
    assert check_frontend_api_key(frontend_api_key_invalid) is False


def test_check_frontend_api_key__non_ascii() -> None:
    assert check_frontend_api_key("é") is False


def test_check_frontend_api_key__valid(frontend_api_key: str) -> None:
    assert check_frontend_api_key(frontend_api_key) is True


def test_verify_frontend_api_key__missing() -> None:
    with pytest.raises(HTTPException) as exc_info:
        verify_frontend_api_key(None)

    error = exc_info.value
    assert error.status_code == status.HTTP_401_UNAUTHORIZED
    assert error.detail[0]["type"] == "frontend_api_key_invalid"  # ty: ignore[invalid-argument-type]


def test_verify_frontend_api_key__invalid(frontend_api_key_invalid: str) -> None:
    with pytest.raises(HTTPException) as exc_info:
        verify_frontend_api_key(frontend_api_key_invalid)

    error = exc_info.value
    assert error.status_code == status.HTTP_401_UNAUTHORIZED
    assert error.detail[0]["type"] == "frontend_api_key_invalid"  # ty: ignore[invalid-argument-type]


def test_verify_frontend_api_key__valid(frontend_api_key: str) -> None:
    assert verify_frontend_api_key(frontend_api_key) is None


def test_get_ip_address__missing() -> None:
    assert get_ip_address().ip_address is None


def test_get_ip_address__malformed(ip_address_malformed: str) -> None:
    assert get_ip_address(ip_address_malformed).ip_address is None


def test_get_ip_address__not_global(ip_address_private: str) -> None:
    assert get_ip_address(ip_address_private).ip_address is None


def test_get_ip_address__global(ip_address_public: str) -> None:
    assert get_ip_address(ip_address_public).ip_address == ip_address_public


def test_get_user_agent__missing() -> None:
    user_agent = get_user_agent()

    assert user_agent.browser is None
    assert user_agent.operating_system is None


def test_get_user_agent__unrecognized(user_agent_unrecognized: str) -> None:
    user_agent = get_user_agent(user_agent_unrecognized)

    assert user_agent.browser is None
    assert user_agent.operating_system is None


def test_get_user_agent__metadata_truncated() -> None:
    browser = "a" * (USER_AGENT_METADATA_MAX_LENGTH + 1)
    parsed_user_agent = get_user_agent(f"{browser}-iPad/1 CFNetwork")

    assert parsed_user_agent.browser == browser[:USER_AGENT_METADATA_MAX_LENGTH]
    assert parsed_user_agent.operating_system == "iOS"


def test_get_user_agent__recognized(user_agent: str) -> None:
    parsed_user_agent = get_user_agent(user_agent)

    assert parsed_user_agent.browser == "Chrome"
    assert parsed_user_agent.operating_system == "Mac OS X"
