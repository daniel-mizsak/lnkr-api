"""
Tests for the timezone dependency.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

import pytest
from fastapi import HTTPException, status

from lnkr.api.dependencies.timezone import get_timezone


def test_get_timezone__defaults_to_utc() -> None:
    assert get_timezone().key == "UTC"


def test_get_timezone__valid_iana_timezone() -> None:
    assert get_timezone("Europe/Copenhagen").key == "Europe/Copenhagen"


def test_get_timezone__invalid_timezone() -> None:
    timezone = "Not/A-Timezone"

    with pytest.raises(HTTPException) as exc_info:
        get_timezone(timezone)

    assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert exc_info.value.detail == [
        {
            "input": timezone,
            "loc": ["query", "timezone"],
            "msg": f"Timezone '{timezone}' is invalid",
            "type": "timezone_invalid",
        }
    ]
