"""
Tests for the delete user endpoint.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from fastapi import status
from sqlalchemy import select

from lnkr.api.dependencies.header import FRONTEND_API_KEY_HEADER
from lnkr.config.application_settings import application_settings
from lnkr.models import LoginToken, RefreshToken, User
from lnkr.services.tokens.access_token_service import create_access_token

if TYPE_CHECKING:
    from httpx2 import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from tests.api.routes.conftest import OverrideGetCurrentUserFunction


async def test_delete_user__user_does_not_exist(client: AsyncClient, session: AsyncSession, user: User) -> None:
    await session.delete(user)
    await session.commit()

    response = await client.delete(url=application_settings.USER_PREFIX)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"][0]["type"] == "user_does_not_exist"


async def test_delete_user__links_and_clicks_removed(
    client: AsyncClient,
    override_get_current_user: OverrideGetCurrentUserFunction,
    user: User,
    user_other: User,
    slug: str,
    slug_other: str,
    target_url: str,
    frontend_api_key: str,
) -> None:
    await client.post(
        url=application_settings.LINKS_PREFIX,
        json={"slug": slug, "target_url": target_url},
    )
    await client.get(
        url=f"{application_settings.FORWARD_PREFIX}/{slug}",
        headers={FRONTEND_API_KEY_HEADER: frontend_api_key},
    )

    response = await client.get(url=f"{application_settings.LINKS_PREFIX}/{slug}/clicks")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data["items"]) == 1

    override_get_current_user(user_other)
    await client.post(
        url=application_settings.LINKS_PREFIX,
        json={"slug": slug_other, "target_url": target_url},
    )
    await client.get(
        url=f"{application_settings.FORWARD_PREFIX}/{slug_other}",
        headers={FRONTEND_API_KEY_HEADER: frontend_api_key},
    )

    override_get_current_user(user)
    response = await client.delete(url=application_settings.USER_PREFIX)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    response = await client.get(
        url=f"{application_settings.FORWARD_PREFIX}/{slug}",
        headers={FRONTEND_API_KEY_HEADER: frontend_api_key},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND

    response = await client.get(
        url=f"{application_settings.FORWARD_PREFIX}/{slug_other}",
        headers={FRONTEND_API_KEY_HEADER: frontend_api_key},
    )
    assert response.status_code == status.HTTP_200_OK

    override_get_current_user(user_other)
    response = await client.get(url=f"{application_settings.LINKS_PREFIX}/{slug_other}/clicks")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data["items"]) == 2

    # Slug can be reused.
    response = await client.post(
        url=application_settings.LINKS_PREFIX,
        json={"slug": slug, "target_url": target_url},
    )

    assert response.status_code == status.HTTP_201_CREATED

    response = await client.get(url=f"{application_settings.LINKS_PREFIX}/{slug}/clicks")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["items"] == []


async def test_delete_user__login_and_refresh_tokens_removed(
    client: AsyncClient,
    session: AsyncSession,
    user: User,
    user_other: User,
) -> None:
    expires_at = datetime.now(tz=UTC) + timedelta(days=1)
    session.add_all(
        [
            LoginToken(email=user.email, token_hash="a" * 64, expires_at=expires_at),
            LoginToken(email=user_other.email, token_hash="b" * 64, expires_at=expires_at),
            RefreshToken(user_id=user.id, token_hash="c" * 64, expires_at=expires_at),
            RefreshToken(user_id=user.id, token_hash="d" * 64, expires_at=expires_at),
            RefreshToken(user_id=user_other.id, token_hash="e" * 64, expires_at=expires_at),
        ]
    )
    await session.commit()

    response = await client.delete(url=application_settings.USER_PREFIX)

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert list((await session.scalars(select(LoginToken.email))).all()) == [user_other.email]
    assert list((await session.scalars(select(RefreshToken.user_id))).all()) == [user_other.id]


@pytest.mark.usefixtures("override_authentication")
async def test_delete_user__access_token_rejected_after_deletion(
    client: AsyncClient,
    user: User,
    user_other: User,
) -> None:
    access_token = create_access_token(user.id)
    other_access_token = create_access_token(user_other.id)

    response = await client.delete(
        url=application_settings.USER_PREFIX,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT

    response = await client.get(
        url=application_settings.USER_PREFIX,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"][0]["type"] == "user_does_not_exist"

    response = await client.get(
        url=application_settings.USER_PREFIX,
        headers={"Authorization": f"Bearer {other_access_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["email"] == user_other.email
