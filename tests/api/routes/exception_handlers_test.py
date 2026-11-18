"""
Regression tests for application-level exception handling.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

from unittest import mock

import pytest
from fastapi import HTTPException, status
from httpx2 import ASGITransport, AsyncClient

from lnkr import exceptions
from lnkr.api.dependencies import auth, get_current_user
from lnkr.config.application_settings import ApplicationEnvironment, application_settings
from lnkr.main import app


def test_exception_handlers__all_domain_errors_registered() -> None:
    domain_errors = {
        error
        for error in vars(exceptions).values()
        if isinstance(error, type) and issubclass(error, exceptions.LnkrError) and error is not exceptions.LnkrError
    }

    missing_handlers = domain_errors.difference(app.exception_handlers)

    assert missing_handlers == set()


@pytest.mark.parametrize(
    ("error", "status_code", "body", "headers"),
    [
        pytest.param(
            exceptions.FrontendApiKeyInvalidError(),
            status.HTTP_401_UNAUTHORIZED,
            {"detail": [{"msg": "The provided frontend api key is invalid", "type": "frontend_api_key_invalid"}]},
            {},
            id="FrontendApiKeyInvalidError",
        ),
        pytest.param(
            exceptions.CursorInvalidError("invalid-cursor"),
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            {
                "detail": [
                    {
                        "input": "invalid-cursor",
                        "loc": ["query", "cursor"],
                        "msg": "The provided cursor is invalid",
                        "type": "cursor_invalid",
                    }
                ]
            },
            {},
            id="CursorInvalidError",
        ),
        pytest.param(
            exceptions.LoginTokenInvalidError(),
            status.HTTP_401_UNAUTHORIZED,
            {
                "detail": [
                    {"msg": "The provided login token is invalid, used or has expired", "type": "login_token_invalid"}
                ]
            },
            {},
            id="LoginTokenInvalidError",
        ),
        pytest.param(
            exceptions.LoginTokenGenerationFailedError(),
            status.HTTP_503_SERVICE_UNAVAILABLE,
            {
                "detail": [
                    {
                        "msg": "Unable to generate a login token. Please try again.",
                        "type": "login_token_generation_failed",
                    }
                ]
            },
            {},
            id="LoginTokenGenerationFailedError",
        ),
        pytest.param(
            exceptions.LoginTokenDeliveryFailedError(),
            status.HTTP_503_SERVICE_UNAVAILABLE,
            {
                "detail": [
                    {
                        "msg": "Unable to send a login token. Please request a new token in 60 seconds.",
                        "type": "login_token_delivery_failed",
                    }
                ]
            },
            {"Cache-Control": "no-store", "Retry-After": "60"},
            id="LoginTokenDeliveryFailedError",
        ),
        pytest.param(
            exceptions.RefreshTokenInvalidError(),
            status.HTTP_401_UNAUTHORIZED,
            {
                "detail": [
                    {
                        "msg": "The provided refresh token is invalid, used, revoked or has expired",
                        "type": "refresh_token_invalid",
                    }
                ]
            },
            {},
            id="RefreshTokenInvalidError",
        ),
        pytest.param(
            exceptions.RefreshTokenGenerationFailedError(),
            status.HTTP_503_SERVICE_UNAVAILABLE,
            {
                "detail": [
                    {
                        "msg": "Unable to generate a refresh token. Please try again.",
                        "type": "refresh_token_generation_failed",
                    }
                ]
            },
            {},
            id="RefreshTokenGenerationFailedError",
        ),
        pytest.param(
            exceptions.UserDoesNotExistError("User with email 'user@example.com' does not exist"),
            status.HTTP_404_NOT_FOUND,
            {"detail": [{"msg": "User with email 'user@example.com' does not exist", "type": "user_does_not_exist"}]},
            {},
            id="UserDoesNotExistError",
        ),
        pytest.param(
            exceptions.UserLinkLimitExceededError("user@example.com", 10),
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            {
                "detail": [
                    {
                        "msg": "User 'user@example.com' exceeds their link limit of 10",
                        "type": "user_link_limit_exceeded",
                    }
                ]
            },
            {},
            id="UserLinkLimitExceededError",
        ),
        pytest.param(
            exceptions.TimezoneInvalidError("Not/A-Timezone"),
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            {
                "detail": [
                    {
                        "input": "Not/A-Timezone",
                        "loc": ["query", "timezone"],
                        "msg": "Timezone 'Not/A-Timezone' is invalid",
                        "type": "timezone_invalid",
                    }
                ]
            },
            {},
            id="TimezoneInvalidError",
        ),
        pytest.param(
            exceptions.SlugAlreadyExistsError("slug"),
            status.HTTP_409_CONFLICT,
            {
                "detail": [
                    {
                        "input": "slug",
                        "loc": ["body", "slug"],
                        "msg": "Slug 'slug' already exists",
                        "type": "slug_already_exists",
                    }
                ]
            },
            {},
            id="SlugAlreadyExistsError",
        ),
        pytest.param(
            exceptions.SlugDoesNotExistError("slug"),
            status.HTTP_404_NOT_FOUND,
            {
                "detail": [
                    {
                        "input": "slug",
                        "loc": ["path", "slug"],
                        "msg": "Slug 'slug' does not exist",
                        "type": "slug_does_not_exist",
                    }
                ]
            },
            {},
            id="SlugDoesNotExistError",
        ),
        pytest.param(
            exceptions.SlugNotOwnedByUserError("slug"),
            status.HTTP_403_FORBIDDEN,
            {
                "detail": [
                    {
                        "input": "slug",
                        "loc": ["path", "slug"],
                        "msg": "Slug 'slug' is not owned by the current user",
                        "type": "slug_not_owned_by_user",
                    }
                ]
            },
            {},
            id="SlugNotOwnedByUserError",
        ),
        pytest.param(
            exceptions.RandomSlugGenerationFailedError(),
            status.HTTP_503_SERVICE_UNAVAILABLE,
            {
                "detail": [
                    {
                        "msg": "Unable to generate an unused random slug. Please try again.",
                        "type": "random_slug_generation_failed",
                    }
                ]
            },
            {"Cache-Control": "no-store"},
            id="RandomSlugGenerationFailedError",
        ),
        pytest.param(
            exceptions.LinkExpiredError("slug"),
            status.HTTP_410_GONE,
            {"detail": [{"msg": "Link with slug 'slug' has expired", "type": "link_expired"}]},
            {"Cache-Control": "no-store"},
            id="LinkExpiredError",
        ),
        pytest.param(
            exceptions.LinkPasswordRequiredError("slug"),
            status.HTTP_401_UNAUTHORIZED,
            {"detail": [{"msg": "Link with slug 'slug' requires a password", "type": "link_password_required"}]},
            {"Cache-Control": "no-store"},
            id="LinkPasswordRequiredError",
        ),
        pytest.param(
            exceptions.LinkPasswordInvalidError("slug"),
            status.HTTP_401_UNAUTHORIZED,
            {
                "detail": [
                    {
                        "msg": "The provided password for link with slug 'slug' is invalid",
                        "type": "link_password_invalid",
                    }
                ]
            },
            {"Cache-Control": "no-store"},
            id="LinkPasswordInvalidError",
        ),
        pytest.param(
            exceptions.LinkDisabledError("slug"),
            status.HTTP_410_GONE,
            {"detail": [{"msg": "Link with slug 'slug' is disabled", "type": "link_disabled"}]},
            {},
            id="LinkDisabledError",
        ),
        pytest.param(
            exceptions.AccessCredentialsMissingError(),
            403,
            {"detail": "Not authenticated"},
            {},
            id="AccessCredentialsMissingError",
        ),
        pytest.param(
            exceptions.AccessTokenMissingError(),
            401,
            {"detail": "Authorization token is missing"},
            {},
            id="AccessTokenMissingError",
        ),
        pytest.param(
            exceptions.AccessTokenInvalidError(), 401, {"detail": "Invalid token"}, {}, id="AccessTokenInvalidError"
        ),
        pytest.param(
            exceptions.AccessTokenSubjectInvalidError(),
            401,
            {"detail": "Invalid token"},
            {},
            id="AccessTokenSubjectInvalidError",
        ),
    ],
)
async def test_exception_handlers__registered_response_contract(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    error: exceptions.LnkrError,
    status_code: int,
    body: dict[str, object],
    headers: dict[str, str],
) -> None:
    def reject() -> None:
        raise error

    monkeypatch.setitem(app.dependency_overrides, get_current_user, reject)

    response = await client.get(application_settings.USER_PREFIX)

    assert response.status_code == status_code
    assert response.headers["content-type"] == "application/json"
    assert response.headers.get("cache-control") == headers.get("Cache-Control")
    assert response.headers.get("retry-after") == headers.get("Retry-After")

    data = response.json()
    assert data == body


async def test_exception_handlers__ordinary_http_exception_unchanged(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def reject() -> None:
        raise HTTPException(status.HTTP_418_IM_A_TEAPOT, detail="ordinary rejection", headers={"X-Reason": "test"})

    monkeypatch.setitem(app.dependency_overrides, get_current_user, reject)

    response = await client.get(application_settings.USER_PREFIX)

    assert response.status_code == status.HTTP_418_IM_A_TEAPOT
    assert response.headers["x-reason"] == "test"

    data = response.json()
    assert data == {"detail": "ordinary rejection"}


async def test_exception_handlers__unexpected_exception_propagates(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def reject() -> None:
        message = "unexpected failure"
        raise RuntimeError(message)

    monkeypatch.setitem(app.dependency_overrides, get_current_user, reject)

    with pytest.raises(RuntimeError, match="unexpected failure"):
        await client.get(application_settings.USER_PREFIX)


@pytest.mark.usefixtures("override_authentication")
async def test_exception_handlers__missing_development_user_remains_server_error(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(application_settings, "ENVIRONMENT", ApplicationEnvironment.DEVELOPMENT)
    error = exceptions.UserDoesNotExistError.by_email(application_settings.DEVELOPMENT_USER_EMAIL)
    monkeypatch.setattr(auth, "get_user_by_email", mock.AsyncMock(side_effect=error))
    transport = ASGITransport(app=app, raise_app_exceptions=False)

    async with AsyncClient(transport=transport, base_url=client.base_url) as error_client:
        response = await error_client.get(application_settings.USER_PREFIX)

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.text == "Internal Server Error"
    assert response.headers["content-type"] == "text/plain; charset=utf-8"
