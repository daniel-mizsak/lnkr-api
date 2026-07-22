"""
Tests for the click service.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

import uuid
from datetime import UTC, datetime
from unittest import mock

from lnkr.models import Click, ClickCursor, ClickSource, Link
from lnkr.services import click_service


async def test_list_clicks__caps_limit_and_encodes_next_cursor(link: Link) -> None:
    session = mock.AsyncMock()
    click = Click(id=uuid.uuid4(), timestamp=datetime.now(tz=UTC), source=ClickSource.LNKR_APP, link_id=link.id)
    list_clicks_by_link = mock.AsyncMock(return_value=([click], True))
    with mock.patch.object(click_service.click_database, "list_clicks_by_link", list_clicks_by_link):
        clicks, next_cursor = await click_service.list_clicks(session, link, 500, None)

    assert clicks == [click]
    assert next_cursor == ClickCursor.from_click(click).encode()
    list_clicks_by_link.assert_awaited_once_with(session, link, 100, None)


async def test_list_clicks__last_page_has_no_cursor(link: Link) -> None:
    session = mock.AsyncMock()
    list_clicks_by_link = mock.AsyncMock(return_value=([], False))
    with mock.patch.object(click_service.click_database, "list_clicks_by_link", list_clicks_by_link):
        clicks, next_cursor = await click_service.list_clicks(session, link, 10, None)

    assert clicks == []
    assert next_cursor is None
