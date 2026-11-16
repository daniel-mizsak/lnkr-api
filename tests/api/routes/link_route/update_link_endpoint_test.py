"""
Tests for the update link endpoint.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
import time_machine
from fastapi import status

from lnkr.config.application_settings import application_settings

if TYPE_CHECKING:
    from httpx2 import AsyncClient

    from lnkr.models import User
    from tests.api.routes.conftest import OverrideGetCurrentUserFunction


async def test_update_link__invalid_target_url(client: AsyncClient, slug: str, target_url_invalid: str) -> None:
    response = await client.patch(
        url=f"{application_settings.LINKS_PREFIX}/{slug}",
        json={"target_url": target_url_invalid},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    data = response.json()
    error = data["detail"][0]

    assert error["input"] == target_url_invalid
    assert error["loc"] == ["body", "target_url"]
    assert error["msg"] == "Input should be a valid URL, relative URL without a base"
    assert error["type"] == "url_parsing"


async def test_update_link__timezone_required(client: AsyncClient, slug: str, target_url: str) -> None:
    await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    response = await client.patch(
        url=f"{application_settings.LINKS_PREFIX}/{slug}",
        json={"expires_at": "2026-12-31T12:00:00"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    data = response.json()
    error = data["detail"][0]

    assert error["loc"] == ["body", "expires_at"]
    assert error["msg"] == "Input should have timezone info"
    assert error["type"] == "timezone_aware"


async def test_update_link__unknown_field(client: AsyncClient, slug: str, target_url: str) -> None:
    await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    response = await client.patch(
        url=f"{application_settings.LINKS_PREFIX}/{slug}",
        json={"taget_url": target_url},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    data = response.json()
    error = data["detail"][0]

    assert error["loc"] == ["body", "taget_url"]
    assert error["type"] == "extra_forbidden"


async def test_update_link__empty_body(client: AsyncClient, slug: str, target_url: str) -> None:
    await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    response = await client.patch(
        url=f"{application_settings.LINKS_PREFIX}/{slug}",
        json={},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    data = response.json()
    error = data["detail"][0]

    assert error["input"] == {}
    assert error["loc"] == ["body"]
    assert error["msg"] == "Value error, At least one field must be provided"
    assert error["type"] == "value_error"


@pytest.mark.parametrize("field", ["target_url", "status", "favorite"])
async def test_update_link__non_nullable_field_cleared(
    client: AsyncClient,
    slug: str,
    target_url: str,
    field: str,
) -> None:
    await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    response = await client.patch(
        url=f"{application_settings.LINKS_PREFIX}/{slug}",
        json={field: None},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    data = response.json()
    error = data["detail"][0]

    assert error["input"] == {field: None}
    assert error["loc"] == ["body"]
    assert error["msg"] == f"Value error, {field} cannot be cleared"
    assert error["type"] == "value_error"


async def test_update_link__slug_does_not_exist(client: AsyncClient, slug: str, target_url: str) -> None:
    response = await client.patch(
        url=f"{application_settings.LINKS_PREFIX}/{slug}",
        json={"target_url": target_url},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND

    data = response.json()
    error = data["detail"][0]

    assert error["input"] == slug
    assert error["loc"] == ["path", "slug"]
    assert error["msg"] == f"Slug '{slug}' does not exist"
    assert error["type"] == "slug_does_not_exist"


async def test_update_link__slug_not_owned_by_user(
    client: AsyncClient,
    override_get_current_user: OverrideGetCurrentUserFunction,
    user_other: User,
    slug: str,
    target_url: str,
) -> None:
    await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    override_get_current_user(user_other)

    response = await client.patch(
        url=f"{application_settings.LINKS_PREFIX}/{slug}",
        json={"target_url": f"{target_url}/1"},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN

    data = response.json()
    error = data["detail"][0]

    assert error["input"] == slug
    assert error["loc"] == ["path", "slug"]
    assert error["msg"] == f"Slug '{slug}' is not owned by the current user"
    assert error["type"] == "slug_not_owned_by_user"


async def test_update_link__target_url_changed(client: AsyncClient, slug: str, target_url: str) -> None:
    await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": f"{target_url}/1"},
    )

    response = await client.patch(
        url=f"{application_settings.LINKS_PREFIX}/{slug}",
        json={"target_url": target_url},
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["target_url"] == target_url


async def test_update_link__expiration_set(
    client: AsyncClient,
    slug: str,
    target_url: str,
    expires_at: datetime,
) -> None:
    await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    response = await client.patch(
        url=f"{application_settings.LINKS_PREFIX}/{slug}",
        json={"expires_at": expires_at.isoformat()},
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert datetime.fromisoformat(data["expires_at"]) == expires_at


async def test_update_link__expiration_cleared(
    client: AsyncClient,
    slug: str,
    target_url: str,
    expires_at: datetime,
) -> None:
    await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url, "expires_at": expires_at.isoformat()},
    )

    response = await client.patch(
        url=f"{application_settings.LINKS_PREFIX}/{slug}",
        json={"expires_at": None},
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["expires_at"] is None


@pytest.mark.parametrize(("original_value", "updated_value"), [("active", "disabled"), ("disabled", "active")])
async def test_update_link__status_changed(
    client: AsyncClient,
    slug: str,
    target_url: str,
    original_value: str,
    updated_value: str,
) -> None:
    await client.post(
        url=application_settings.LINKS_PREFIX,
        json={"slug": slug, "target_url": target_url},
    )
    await client.patch(
        url=f"{application_settings.LINKS_PREFIX}/{slug}",
        json={"status": original_value},
    )

    response = await client.patch(
        url=f"{application_settings.LINKS_PREFIX}/{slug}",
        json={"status": updated_value},
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["status"] == updated_value


@pytest.mark.parametrize(("original_value", "updated_value"), [(False, True), (True, False)])
async def test_update_link__favorite_changed(
    client: AsyncClient,
    slug: str,
    target_url: str,
    original_value: bool,
    updated_value: bool,
) -> None:
    await client.post(
        url=application_settings.LINKS_PREFIX,
        json={"slug": slug, "target_url": target_url},
    )
    await client.patch(
        url=f"{application_settings.LINKS_PREFIX}/{slug}",
        json={"favorite": original_value},
    )

    response = await client.patch(
        url=f"{application_settings.LINKS_PREFIX}/{slug}",
        json={"favorite": updated_value},
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["favorite"] == updated_value


@pytest.mark.parametrize(
    ("original_password", "updated_password", "password_protected"),
    [
        pytest.param(None, "password", True, id="set"),
        pytest.param("password", None, False, id="clear"),
    ],
)
async def test_update_link__password_protection_changed(
    client: AsyncClient,
    slug: str,
    target_url: str,
    original_password: str | None,
    updated_password: str | None,
    password_protected: bool,
) -> None:
    await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url, "password": original_password},
    )

    response = await client.patch(
        url=f"{application_settings.LINKS_PREFIX}/{slug}",
        json={"password": updated_password},
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["password_protected"] is password_protected


async def test_update_link__password_replaced(client: AsyncClient, slug: str, target_url: str, password: str) -> None:
    await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url, "password": password},
    )

    response = await client.patch(
        url=f"{application_settings.LINKS_PREFIX}/{slug}",
        json={"password": f"new-{password}"},
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["password_protected"] is True

    old_password_response = await client.post(
        url=f"{application_settings.FORWARD_PREFIX}/{slug}/unlock",
        json={"password": password},
    )
    new_password_response = await client.post(
        url=f"{application_settings.FORWARD_PREFIX}/{slug}/unlock",
        json={"password": f"new-{password}"},
    )
    assert old_password_response.status_code == status.HTTP_401_UNAUTHORIZED
    assert new_password_response.status_code == status.HTTP_200_OK

    data = new_password_response.json()
    assert data["target_url"] == target_url


async def test_update_link__created_at_preserved(client: AsyncClient, slug: str, target_url: str) -> None:
    created_at = datetime(2026, 1, 1, 12, tzinfo=UTC)
    updated_at = created_at + timedelta(minutes=1)

    with time_machine.travel(created_at, tick=False) as traveller:
        await client.post(
            url=f"{application_settings.LINKS_PREFIX}",
            json={"slug": slug, "target_url": target_url},
        )
        traveller.move_to(updated_at)

        response = await client.patch(
            url=f"{application_settings.LINKS_PREFIX}/{slug}",
            json={"target_url": f"{target_url}/1"},
        )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert datetime.fromisoformat(data["created_at"]) == created_at


async def test_update_link__updated_at_advanced(client: AsyncClient, slug: str, target_url: str) -> None:
    created_at = datetime(2026, 1, 1, 12, tzinfo=UTC)
    updated_at = created_at + timedelta(minutes=1)

    with time_machine.travel(created_at, tick=False) as traveller:
        await client.post(
            url=f"{application_settings.LINKS_PREFIX}",
            json={"slug": slug, "target_url": target_url},
        )
        traveller.move_to(updated_at)

        response = await client.patch(
            url=f"{application_settings.LINKS_PREFIX}/{slug}",
            json={"target_url": f"{target_url}/1"},
        )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert datetime.fromisoformat(data["updated_at"]) == updated_at
