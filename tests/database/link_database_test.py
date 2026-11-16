"""
Tests for link database operations.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

import uuid
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from lnkr.database import link_database
from lnkr.models import Link

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from lnkr.models import User


async def test_get_link_slugs_by_user__all_owned_slugs_only(
    session: AsyncSession,
    user: User,
    user_other: User,
    target_url: str,
) -> None:
    slugs = [f"slug-{index}" for index in range(100)]
    session.add_all([Link(slug=slug, target_url=target_url, user=user) for slug in slugs])
    session.add(Link(slug="other", target_url=target_url, user=user_other))
    await session.commit()

    owned_slugs = await link_database.get_link_slugs_by_user(session, user.id)

    assert set(owned_slugs) == set(slugs)


async def test_get_link_slugs_by_user__user_does_not_exist(session: AsyncSession, link: Link) -> None:
    session.add(link)
    await session.commit()
    user_id = uuid.uuid4()

    slugs = await link_database.get_link_slugs_by_user(session, user_id)

    assert slugs == []


@pytest.mark.parametrize(
    ("search", "page", "expected_page"),
    [
        pytest.param("MATCH", 1, (2, ["match-one"]), id="first-page"),
        pytest.param("MATCH", 2, (2, ["unrelated-slug"]), id="second-page"),
        pytest.param("missing", 1, (0, []), id="no-matches"),
    ],
)
async def test_list_links_by_user__filters_counts_and_paginates(
    session: AsyncSession,
    user: User,
    user_other: User,
    target_url: str,
    search: str,
    page: int,
    expected_page: tuple[int, list[str]],
    now: datetime,
) -> None:
    expected_total, expected_slugs = expected_page
    target_url_match_slug = "unrelated-slug"
    links = [
        Link(
            slug="match-one",
            target_url=target_url,
            favorite=False,
            created_at=now,
            updated_at=now,
            user=user,
        ),
        Link(
            slug=target_url_match_slug,
            target_url="https://match.example.com",
            favorite=True,
            created_at=now + timedelta(seconds=1),
            updated_at=now + timedelta(seconds=1),
            user=user,
        ),
        Link(
            slug="not-a-match",
            target_url=target_url,
            favorite=True,
            created_at=now + timedelta(seconds=2),
            updated_at=now + timedelta(seconds=2),
            user=user_other,
        ),
    ]
    session.add_all(links)
    await session.commit()

    links, total = await link_database.list_links_by_user(
        session,
        user,
        search=search,
        favorites_only=False,
        sort="created_at",
        direction="ascending",
        per_page=1,
        page=page,
    )

    assert total == expected_total
    assert [link.slug for link in links] == expected_slugs


@pytest.mark.parametrize(
    ("favorites_only", "expected_ids"),
    [pytest.param(True, [2, 1], id="favorites"), pytest.param(False, [3, 2, 1], id="all-links")],
)
async def test_list_links_by_user__favorites_and_id_tie_breaker(
    session: AsyncSession,
    user: User,
    target_url: str,
    favorites_only: bool,
    expected_ids: list[int],
    now: datetime,
) -> None:
    link_ids = [uuid.UUID(int=value) for value in range(1, 4)]
    session.add_all(
        [
            Link(
                id=link_ids[0],
                slug="favorite-one",
                target_url=target_url,
                favorite=True,
                created_at=now,
                updated_at=now,
                user=user,
            ),
            Link(
                id=link_ids[1],
                slug="favorite-two",
                target_url=target_url,
                favorite=True,
                created_at=now,
                updated_at=now,
                user=user,
            ),
            Link(
                id=link_ids[2],
                slug="not-favorite",
                target_url=target_url,
                favorite=False,
                created_at=now,
                updated_at=now,
                user=user,
            ),
        ]
    )
    await session.commit()

    links, total = await link_database.list_links_by_user(
        session,
        user,
        search=None,
        favorites_only=favorites_only,
        sort="updated_at",
        direction="descending",
        per_page=10,
        page=1,
    )

    assert total == len(expected_ids)
    assert [link.id for link in links] == [uuid.UUID(int=value) for value in expected_ids]
