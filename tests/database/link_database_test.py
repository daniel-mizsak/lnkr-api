"""
Tests for non-trivial link database queries.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from lnkr.database import link_database
from lnkr.models import Link

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from lnkr.models import User


async def test_list_links_by_user__filters_counts_and_paginates(
    session: AsyncSession,
    user: User,
    user_other: User,
    target_url: str,
) -> None:
    timestamp = datetime.now(tz=UTC)
    target_url_match_slug = "unrelated-slug"
    links = [
        Link(
            slug="match-one",
            target_url=target_url,
            favorite=False,
            created_at=timestamp,
            updated_at=timestamp,
            user=user,
        ),
        Link(
            slug=target_url_match_slug,
            target_url="https://match.example.com",
            favorite=True,
            created_at=timestamp + timedelta(seconds=1),
            updated_at=timestamp + timedelta(seconds=1),
            user=user,
        ),
        Link(
            slug="not-a-match",
            target_url=target_url,
            favorite=True,
            created_at=timestamp + timedelta(seconds=2),
            updated_at=timestamp + timedelta(seconds=2),
            user=user_other,
        ),
    ]
    session.add_all(links)
    await session.commit()

    first_page, first_page_total = await link_database.list_links_by_user(
        session,
        user,
        search="MATCH",
        favorites_only=False,
        sort="created_at",
        direction="ascending",
        per_page=1,
        page=1,
    )
    second_page, second_page_total = await link_database.list_links_by_user(
        session,
        user,
        search="MATCH",
        favorites_only=False,
        sort="created_at",
        direction="ascending",
        per_page=1,
        page=2,
    )

    assert first_page_total == 2
    assert [link.slug for link in first_page] == ["match-one"]
    assert second_page_total == 2
    assert [link.slug for link in second_page] == [target_url_match_slug]

    no_matches, no_match_total = await link_database.list_links_by_user(
        session,
        user,
        search="missing",
        favorites_only=False,
        sort="created_at",
        direction="ascending",
        per_page=10,
        page=1,
    )
    assert no_matches == []
    assert no_match_total == 0


async def test_list_links_by_user__favorites_and_id_tie_breaker(
    session: AsyncSession,
    user: User,
    target_url: str,
) -> None:
    timestamp = datetime.now(tz=UTC)
    link_ids = [uuid.UUID(int=value) for value in range(1, 4)]
    session.add_all(
        [
            Link(
                id=link_ids[0],
                slug="favorite-one",
                target_url=target_url,
                favorite=True,
                created_at=timestamp,
                updated_at=timestamp,
                user=user,
            ),
            Link(
                id=link_ids[1],
                slug="favorite-two",
                target_url=target_url,
                favorite=True,
                created_at=timestamp,
                updated_at=timestamp,
                user=user,
            ),
            Link(
                id=link_ids[2],
                slug="not-favorite",
                target_url=target_url,
                favorite=False,
                created_at=timestamp,
                updated_at=timestamp,
                user=user,
            ),
        ]
    )
    await session.commit()

    links, total = await link_database.list_links_by_user(
        session,
        user,
        search=None,
        favorites_only=True,
        sort="updated_at",
        direction="descending",
        per_page=10,
        page=1,
    )

    assert total == 2
    assert [link.id for link in links] == [link_ids[1], link_ids[0]]

    all_links, all_links_total = await link_database.list_links_by_user(
        session,
        user,
        search=None,
        favorites_only=False,
        sort="updated_at",
        direction="descending",
        per_page=10,
        page=1,
    )

    assert all_links_total == 3
    assert [link.id for link in all_links] == [link_ids[2], link_ids[1], link_ids[0]]
