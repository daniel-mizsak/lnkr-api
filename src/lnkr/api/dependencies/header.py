"""
FastAPI dependency that provides request headers.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

import hmac
import ipaddress
from typing import Annotated

from fastapi import Header
from ua_parser import parse

from lnkr.config.application_settings import application_settings
from lnkr.exceptions import FrontendApiKeyInvalidError
from lnkr.models import IpAddress, UserAgent
from lnkr.models.constraints import USER_AGENT_METADATA_MAX_LENGTH

FRONTEND_API_KEY_HEADER = "X-Frontend-Api-Key"
CLIENT_IP_HEADER = "X-Client-IP"
USER_AGENT_HEADER = "User-Agent"


def check_frontend_api_key(
    x_frontend_api_key: Annotated[str | None, Header(alias=FRONTEND_API_KEY_HEADER)] = None,
) -> bool:
    """Check if the provided frontend API key is valid."""
    return _api_key_matches(x_frontend_api_key)


def verify_frontend_api_key(
    x_frontend_api_key: Annotated[str | None, Header(alias=FRONTEND_API_KEY_HEADER)] = None,
) -> None:
    """Verify that the provided frontend API key is valid."""
    if not _api_key_matches(x_frontend_api_key):
        FrontendApiKeyInvalidError().raise_http_exception()


def _api_key_matches(provided_api_key: str | None) -> bool:
    if provided_api_key is None:
        return False
    expected_api_key = application_settings.FRONTEND_API_KEY.get_secret_value()
    return hmac.compare_digest(provided_api_key.encode(), expected_api_key.encode())


def get_ip_address(
    x_client_ip: Annotated[str | None, Header(alias=CLIENT_IP_HEADER)] = None,
) -> IpAddress:
    """Get IP address from request header."""
    if x_client_ip is None:
        return IpAddress()

    try:
        ip_address = ipaddress.ip_address(x_client_ip.strip())
    except ValueError:
        return IpAddress()

    # Only record clicks from globally routable addresses.
    if not ip_address.is_global:
        return IpAddress()

    return IpAddress(ip_address=str(ip_address))


def get_user_agent(
    user_agent: Annotated[str | None, Header(alias=USER_AGENT_HEADER)] = None,
) -> UserAgent:
    """Get user agent from request header."""
    if user_agent is None:
        return UserAgent()

    parsed_user_agent = parse(user_agent)

    browser: str | None = None
    if parsed_user_agent.user_agent:
        browser = parsed_user_agent.user_agent.family[:USER_AGENT_METADATA_MAX_LENGTH]
    operating_system: str | None = None
    if parsed_user_agent.os:
        operating_system = parsed_user_agent.os.family[:USER_AGENT_METADATA_MAX_LENGTH]

    return UserAgent(browser=browser, operating_system=operating_system)
