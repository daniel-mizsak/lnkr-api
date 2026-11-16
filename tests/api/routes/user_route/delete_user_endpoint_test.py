"""
Tests for the delete user endpoint.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING

import pytest
from fastapi import status
from sqlalchemy import select

from lnkr.config.application_settings import application_settings
from lnkr.models import Click, Link, LoginToken, RefreshToken, User

if TYPE_CHECKING:
    from httpx2 import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from tests.api.routes.conftest import IssueAuthTokensFunction, OverrideGetCurrentUserFunction


async def test_delete_user__user_does_not_exist(client: AsyncClient) -> None:
    await client.delete(url=application_settings.USER_PREFIX)

    response = await client.delete(url=application_settings.USER_PREFIX)

    assert response.status_code == status.HTTP_404_NOT_FOUND

    data = response.json()
    error = data["detail"][0]

    assert error["type"] == "user_does_not_exist"


async def test_delete_user__links_and_clicks_removed(
    client: AsyncClient,
    session: AsyncSession,
    override_get_current_user: OverrideGetCurrentUserFunction,
    user: User,
    user_other: User,
    slug: str,
    slug_other: str,
    target_url: str,
) -> None:
    await client.post(
        url=application_settings.LINKS_PREFIX,
        json={"slug": slug, "target_url": target_url},
    )
    await client.get(url=f"{application_settings.FORWARD_PREFIX}/{slug}")
    await client.get(url=f"{application_settings.FORWARD_PREFIX}/{slug}")

    response = await client.get(url=f"{application_settings.LINKS_PREFIX}/{slug}/clicks")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert len(data["items"]) == 2

    override_get_current_user(user_other)
    await client.post(
        url=application_settings.LINKS_PREFIX,
        json={"slug": slug_other, "target_url": target_url},
    )
    await client.get(url=f"{application_settings.FORWARD_PREFIX}/{slug_other}")
    await client.get(url=f"{application_settings.FORWARD_PREFIX}/{slug_other}")
    override_get_current_user(user)

    response = await client.delete(url=application_settings.USER_PREFIX)

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert list((await session.scalars(select(Link.slug))).all()) == [slug_other]
    assert list((await session.scalars(select(Link.slug).join(Click))).all()) == [slug_other, slug_other]

    deleted_link_response = await client.get(url=f"{application_settings.FORWARD_PREFIX}/{slug}")
    other_link_response = await client.get(url=f"{application_settings.FORWARD_PREFIX}/{slug_other}")
    assert deleted_link_response.status_code == status.HTTP_404_NOT_FOUND
    assert other_link_response.status_code == status.HTTP_200_OK


async def test_delete_user__slug_reused_after_deletion(
    client: AsyncClient,
    session: AsyncSession,
    override_get_current_user: OverrideGetCurrentUserFunction,
    user_other: User,
    slug: str,
    target_url: str,
) -> None:
    await client.post(
        url=application_settings.LINKS_PREFIX,
        json={"slug": slug, "target_url": target_url},
    )
    await client.get(url=f"{application_settings.FORWARD_PREFIX}/{slug}")

    response = await client.get(url=f"{application_settings.LINKS_PREFIX}/{slug}/clicks")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert len(data["items"]) == 1

    await client.delete(url=application_settings.USER_PREFIX)
    override_get_current_user(user_other)

    response = await client.post(
        url=application_settings.LINKS_PREFIX,
        json={"slug": slug, "target_url": target_url},
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert list((await session.scalars(select(Click.id))).all()) == []


async def test_delete_user__login_and_refresh_tokens_removed(
    client: AsyncClient,
    session: AsyncSession,
    user: User,
    user_other: User,
    issue_auth_tokens: IssueAuthTokensFunction,
) -> None:
    await issue_auth_tokens(user.email)
    await issue_auth_tokens(user.email)
    await issue_auth_tokens(user_other.email)

    response = await client.delete(url=application_settings.USER_PREFIX)

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert list((await session.scalars(select(LoginToken.email))).all()) == [user_other.email]
    assert list((await session.scalars(select(RefreshToken.user_id))).all()) == [user_other.id]


@pytest.mark.usefixtures("override_authentication")
async def test_delete_user__access_token_rejected_after_deletion(
    client: AsyncClient,
    user: User,
    user_other: User,
    issue_auth_tokens: IssueAuthTokensFunction,
) -> None:
    auth_tokens = await issue_auth_tokens(user.email)
    other_auth_tokens = await issue_auth_tokens(user_other.email)

    response = await client.delete(
        url=application_settings.USER_PREFIX,
        headers={"Authorization": f"Bearer {auth_tokens['access_token']}"},
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT

    deleted_user_response = await client.get(
        url=application_settings.USER_PREFIX,
        headers={"Authorization": f"Bearer {auth_tokens['access_token']}"},
    )
    other_user_response = await client.get(
        url=application_settings.USER_PREFIX,
        headers={"Authorization": f"Bearer {other_auth_tokens['access_token']}"},
    )
    assert deleted_user_response.status_code == status.HTTP_404_NOT_FOUND

    data = deleted_user_response.json()
    error = data["detail"][0]

    assert error["type"] == "user_does_not_exist"
    assert other_user_response.status_code == status.HTTP_200_OK

    data = other_user_response.json()
    assert data["email"] == user_other.email
