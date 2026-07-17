"""
FastAPI dependencies for pagination parameters.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import Annotated

from fastapi import Query

from lnkr.exceptions import CursorInvalidError
from lnkr.models import ClickCursor
from lnkr.models.click_model import CLICK_CURSOR_MAX_LENGTH


def get_click_cursor(
    cursor: Annotated[str | None, Query(max_length=CLICK_CURSOR_MAX_LENGTH)] = None,
) -> ClickCursor | None:
    """Decode and validate a click pagination cursor."""
    if cursor is None:
        return None

    try:
        return ClickCursor.decode(cursor)
    except ValueError:
        CursorInvalidError(cursor).raise_http_exception()
