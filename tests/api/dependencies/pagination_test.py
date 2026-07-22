"""
Tests for pagination dependencies.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

import uuid
from datetime import UTC, datetime

import pytest
from fastapi import HTTPException, status

from lnkr.api.dependencies.pagination import get_click_cursor
from lnkr.models import ClickCursor


def test_get_click_cursor__missing() -> None:
    assert get_click_cursor() is None


def test_get_click_cursor__maps_invalid_cursor_to_http_error() -> None:
    with pytest.raises(HTTPException) as exc_info:
        get_click_cursor("invalid")

    assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert exc_info.value.detail[0]["type"] == "cursor_invalid"  # ty: ignore[invalid-argument-type]


def test_get_click_cursor__decodes_valid_cursor() -> None:
    cursor = ClickCursor(timestamp=datetime.now(tz=UTC), id=uuid.uuid4())

    assert get_click_cursor(cursor.encode()) == cursor
