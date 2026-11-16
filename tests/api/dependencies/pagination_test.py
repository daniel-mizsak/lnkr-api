"""
Tests for pagination dependencies.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

import uuid
from typing import TYPE_CHECKING

import pytest
from fastapi import HTTPException, status

from lnkr.api.dependencies.pagination import get_click_cursor
from lnkr.models import ClickCursor

if TYPE_CHECKING:
    from datetime import datetime


def test_get_click_cursor__missing() -> None:
    cursor = get_click_cursor()

    assert cursor is None


def test_get_click_cursor__invalid_cursor() -> None:
    with pytest.raises(HTTPException) as exc_info:
        get_click_cursor("invalid")

    assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert exc_info.value.detail[0]["type"] == "cursor_invalid"  # ty: ignore[invalid-argument-type]


def test_get_click_cursor__valid_cursor(now: datetime) -> None:
    cursor = ClickCursor(timestamp=now, id=uuid.uuid4())

    decoded_cursor = get_click_cursor(cursor.encode())

    assert decoded_cursor == cursor
