"""
Tests for the update link endpoint.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from datetime import datetime
from typing import TYPE_CHECKING

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
    data = response.json()

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    error = data["detail"][0]
    assert error["input"] == target_url_invalid
    assert error["loc"] == ["body", "target_url"]
    assert error["msg"] == "Input should be a valid URL, relative URL without a base"
    assert error["type"] == "url_parsing"


async def test_update_link__slug_does_not_exist(client: AsyncClient, slug: str, target_url: str) -> None:
    response = await client.patch(
        url=f"{application_settings.LINKS_PREFIX}/{slug}",
        json={"target_url": target_url},
    )
    data = response.json()

    assert response.status_code == status.HTTP_404_NOT_FOUND
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
    data = response.json()

    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = data["detail"][0]
    assert error["input"] == slug
    assert error["loc"] == ["path", "slug"]
    assert error["msg"] == f"Slug '{slug}' is not owned by the current user"
    assert error["type"] == "slug_not_owned_by_user"


async def test_update_link__unknown_field(client: AsyncClient, slug: str, target_url: str) -> None:
    await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    response = await client.patch(
        url=f"{application_settings.LINKS_PREFIX}/{slug}",
        json={"taget_url": target_url},
    )
    data = response.json()

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
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
    data = response.json()

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    error = data["detail"][0]
    assert error["input"] == {}
    assert error["loc"] == ["body"]
    assert error["msg"] == "Value error, At least one field must be provided"
    assert error["type"] == "value_error"


async def test_update_link__target_url(client: AsyncClient, slug: str, target_url: str) -> None:
    await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": f"{target_url}/1"},
    )

    response = await client.patch(
        url=f"{application_settings.LINKS_PREFIX}/{slug}",
        json={"target_url": target_url},
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["target_url"] == target_url


async def test_update_link__null_target_url(client: AsyncClient, slug: str, target_url: str) -> None:
    await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    response = await client.patch(
        url=f"{application_settings.LINKS_PREFIX}/{slug}",
        json={"target_url": None},
    )
    data = response.json()

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    error = data["detail"][0]
    assert error["input"] == {"target_url": None}
    assert error["loc"] == ["body"]
    assert error["msg"] == "Value error, target_url cannot be cleared"
    assert error["type"] == "value_error"


async def test_update_link__status(client: AsyncClient, slug: str, target_url: str) -> None:
    await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    response = await client.patch(
        url=f"{application_settings.LINKS_PREFIX}/{slug}",
        json={"status": "disabled"},
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["status"] == "disabled"

    response = await client.patch(
        url=f"{application_settings.LINKS_PREFIX}/{slug}",
        json={"status": "active"},
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["status"] == "active"


async def test_update_link__null_status(client: AsyncClient, slug: str, target_url: str) -> None:
    await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    response = await client.patch(
        url=f"{application_settings.LINKS_PREFIX}/{slug}",
        json={"status": None},
    )
    data = response.json()

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    error = data["detail"][0]
    assert error["input"] == {"status": None}
    assert error["loc"] == ["body"]
    assert error["msg"] == "Value error, status cannot be cleared"
    assert error["type"] == "value_error"


async def test_update_link__favorite(client: AsyncClient, slug: str, target_url: str) -> None:
    await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    response = await client.patch(
        url=f"{application_settings.LINKS_PREFIX}/{slug}",
        json={"favorite": True},
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["favorite"] is True

    response = await client.patch(
        url=f"{application_settings.LINKS_PREFIX}/{slug}",
        json={"favorite": False},
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["favorite"] is False


async def test_update_link__null_favorite(client: AsyncClient, slug: str, target_url: str) -> None:
    await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    response = await client.patch(
        url=f"{application_settings.LINKS_PREFIX}/{slug}",
        json={"favorite": None},
    )
    data = response.json()

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    error = data["detail"][0]
    assert error["input"] == {"favorite": None}
    assert error["loc"] == ["body"]
    assert error["msg"] == "Value error, favorite cannot be cleared"
    assert error["type"] == "value_error"


async def test_update_link__expires_at(
    client: AsyncClient,
    slug: str,
    target_url: str,
    expires_at_future: datetime,
) -> None:
    await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    response = await client.patch(
        url=f"{application_settings.LINKS_PREFIX}/{slug}",
        json={"expires_at": expires_at_future.isoformat()},
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert datetime.fromisoformat(data["expires_at"]) == expires_at_future

    response = await client.patch(
        url=f"{application_settings.LINKS_PREFIX}/{slug}",
        json={"expires_at": None},
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["expires_at"] is None


async def test_update_link__expires_at_aware_datetime(client: AsyncClient, slug: str, target_url: str) -> None:
    await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    response = await client.patch(
        url=f"{application_settings.LINKS_PREFIX}/{slug}",
        json={"expires_at": "2026-12-31T12:00:00"},
    )
    data = response.json()

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    error = data["detail"][0]
    assert error["loc"] == ["body", "expires_at"]
    assert error["msg"] == "Input should have timezone info"
    assert error["type"] == "timezone_aware"


async def test_update_link__password(client: AsyncClient, slug: str, target_url: str, password: str) -> None:
    await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    response = await client.patch(
        url=f"{application_settings.LINKS_PREFIX}/{slug}",
        json={"password": password},
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["password_protected"] is True

    # Change password
    response = await client.patch(
        url=f"{application_settings.LINKS_PREFIX}/{slug}",
        json={"password": f"new-{password}"},
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["password_protected"] is True

    response = await client.post(
        url=f"{application_settings.FORWARD_PREFIX}/{slug}/unlock",
        json={"password": password},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    response = await client.post(
        url=f"{application_settings.FORWARD_PREFIX}/{slug}/unlock",
        json={"password": f"new-{password}"},
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["target_url"] == target_url

    # Clear password
    response = await client.patch(
        url=f"{application_settings.LINKS_PREFIX}/{slug}",
        json={"password": None},
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["password_protected"] is False


async def test_update_link__created_at(
    client: AsyncClient,
    slug: str,
    target_url: str,
) -> None:
    response = await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )
    data = response.json()
    original_created_at = data["created_at"]

    response = await client.patch(
        url=f"{application_settings.LINKS_PREFIX}/{slug}",
        json={"target_url": f"{target_url}/1"},
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["created_at"] == original_created_at


async def test_update_link__updated_at(
    client: AsyncClient,
    slug: str,
    target_url: str,
) -> None:
    response = await client.post(
        url=f"{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )
    data = response.json()
    original_updated_at = data["updated_at"]

    response = await client.patch(
        url=f"{application_settings.LINKS_PREFIX}/{slug}",
        json={"target_url": f"{target_url}/1"},
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["updated_at"] > original_updated_at
