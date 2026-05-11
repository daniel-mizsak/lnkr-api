"""
FastAPI dependencies that verify the request originates from the frontend.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

import hmac
from typing import Annotated

from fastapi import Header

from lnkr.config.application_settings import application_settings
from lnkr.exceptions import FrontendApiKeyInvalidError

FRONTEND_API_KEY_HEADER = "X-Frontend-Api-Key"


async def check_frontend_api_key(
    x_frontend_api_key: Annotated[str | None, Header(alias=FRONTEND_API_KEY_HEADER)] = None,
) -> bool:
    """Check if the provided frontend API key is valid."""
    return _api_key_matches(x_frontend_api_key)


async def verify_frontend_api_key(
    x_frontend_api_key: Annotated[str | None, Header(alias=FRONTEND_API_KEY_HEADER)] = None,
) -> None:
    """Verify that the provided frontend API key is valid."""
    if not _api_key_matches(x_frontend_api_key):
        FrontendApiKeyInvalidError().raise_http_exception()


def _api_key_matches(provided_api_key: str | None) -> bool:
    if provided_api_key is None:
        return False
    expected_api_key = application_settings.FRONTEND_API_KEY.get_secret_value()
    return hmac.compare_digest(provided_api_key, expected_api_key)
