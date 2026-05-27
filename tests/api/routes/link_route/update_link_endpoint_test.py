"""
Tests for the update link endpoint.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from datetime import datetime
from typing import TYPE_CHECKING

from fastapi import status

from lnkr.config.application_settings import application_settings

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from lnkr.models import User
    from tests.api.conftest import OverrideGetCurrentUserFunction


def test_update_link__invalid_target_url(client: TestClient, slug: str, target_url_invalid: str) -> None:
    response = client.patch(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}/{slug}",
        json={"target_url": target_url_invalid},
    )
    data = response.json()

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    error = data["detail"][0]
    assert error["input"] == target_url_invalid
    assert error["loc"] == ["body", "target_url"]
    assert error["msg"] == "Input should be a valid URL, relative URL without a base"
    assert error["type"] == "url_parsing"


def test_update_link__slug_does_not_exist(client: TestClient, slug: str, target_url: str) -> None:
    response = client.patch(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}/{slug}",
        json={"target_url": target_url},
    )
    data = response.json()

    assert response.status_code == status.HTTP_404_NOT_FOUND
    error = data["detail"][0]
    assert error["input"] == slug
    assert error["loc"] == ["path", "slug"]
    assert error["msg"] == f"Slug '{slug}' does not exist"
    assert error["type"] == "slug_does_not_exist"


def test_update_link__slug_not_owned_by_user(
    client: TestClient,
    override_get_current_user: OverrideGetCurrentUserFunction,
    other_user: User,
    slug: str,
    target_url: str,
) -> None:
    client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    override_get_current_user(other_user)
    response = client.patch(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}/{slug}",
        json={"target_url": f"{target_url}/1"},
    )
    data = response.json()

    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = data["detail"][0]
    assert error["input"] == slug
    assert error["loc"] == ["path", "slug"]
    assert error["msg"] == f"Slug '{slug}' is not owned by the current user"
    assert error["type"] == "slug_not_owned_by_user"


def test_update_link__unknown_field_rejected(client: TestClient, slug: str, target_url: str) -> None:
    client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    response = client.patch(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}/{slug}",
        json={"taget_url": target_url},
    )
    data = response.json()

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    error = data["detail"][0]
    assert error["loc"] == ["body", "taget_url"]
    assert error["type"] == "extra_forbidden"


def test_update_link__empty_body_rejected(client: TestClient, slug: str, target_url: str) -> None:
    client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    response = client.patch(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}/{slug}",
        json={},
    )
    data = response.json()

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    error = data["detail"][0]
    assert error["input"] == {}
    assert error["loc"] == ["body"]
    assert error["msg"] == "Value error, At least one field must be provided"
    assert error["type"] == "value_error"


def test_update_link__target_url(client: TestClient, slug: str, target_url: str) -> None:
    client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": f"{target_url}/1"},
    )

    response = client.patch(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}/{slug}",
        json={"target_url": target_url},
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["target_url"] == target_url


def test_update_link__cannot_clear_target_url(client: TestClient, slug: str, target_url: str) -> None:
    client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    response = client.patch(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}/{slug}",
        json={"target_url": None},
    )
    data = response.json()

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    error = data["detail"][0]
    assert error["input"] == {"target_url": None}
    assert error["loc"] == ["body"]
    assert error["msg"] == "Value error, target_url cannot be cleared"
    assert error["type"] == "value_error"


def test_update_link__status(client: TestClient, slug: str, target_url: str) -> None:
    client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    response = client.patch(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}/{slug}",
        json={"status": "disabled"},
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["status"] == "disabled"

    response = client.patch(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}/{slug}",
        json={"status": "active"},
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["status"] == "active"


def test_update_link__cannot_clear_status(client: TestClient, slug: str, target_url: str) -> None:
    client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    response = client.patch(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}/{slug}",
        json={"status": None},
    )
    data = response.json()

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    error = data["detail"][0]
    assert error["input"] == {"status": None}
    assert error["loc"] == ["body"]
    assert error["msg"] == "Value error, status cannot be cleared"
    assert error["type"] == "value_error"


def test_update_link__expires_at(client: TestClient, slug: str, target_url: str, future_expires_at: datetime) -> None:
    client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    response = client.patch(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}/{slug}",
        json={"expires_at": future_expires_at.isoformat()},
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert datetime.fromisoformat(data["expires_at"]) == future_expires_at

    response = client.patch(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}/{slug}",
        json={"expires_at": None},
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["expires_at"] is None


def test_update_link__expires_at_aware_datetime(client: TestClient, slug: str, target_url: str) -> None:
    client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    response = client.patch(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}/{slug}",
        json={"expires_at": "2026-12-31T12:00:00"},
    )
    data = response.json()

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    error = data["detail"][0]
    assert error["loc"] == ["body", "expires_at"]
    assert error["msg"] == "Input should have timezone info"
    assert error["type"] == "timezone_aware"


def test_update_link__password(client: TestClient, slug: str, target_url: str, password: str) -> None:
    client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )

    response = client.patch(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}/{slug}",
        json={"password": password},
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["password_protected"] is True

    # Change password
    response = client.patch(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}/{slug}",
        json={"password": f"new-{password}"},
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["password_protected"] is True

    response = client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.FORWARD_PREFIX}/{slug}/unlock",
        json={"password": password},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    response = client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.FORWARD_PREFIX}/{slug}/unlock",
        json={"password": f"new-{password}"},
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["target_url"] == target_url

    # Clear password
    response = client.patch(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}/{slug}",
        json={"password": None},
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["password_protected"] is False


def test_update_link__created_at(
    client: TestClient,
    slug: str,
    target_url: str,
) -> None:
    response = client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )
    data = response.json()
    original_created_at = data["created_at"]

    response = client.patch(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}/{slug}",
        json={"target_url": f"{target_url}/1"},
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["created_at"] == original_created_at


def test_update_link__updated_at(
    client: TestClient,
    slug: str,
    target_url: str,
) -> None:
    response = client.post(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}",
        json={"slug": slug, "target_url": target_url},
    )
    data = response.json()
    original_updated_at = data["updated_at"]

    response = client.patch(
        url=f"{application_settings.API_VERSION_PREFIX}{application_settings.LINKS_PREFIX}/{slug}",
        json={"target_url": f"{target_url}/1"},
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["updated_at"] > original_updated_at
