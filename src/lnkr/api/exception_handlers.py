"""
HTTP responses for domain errors.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

import logging
from typing import TYPE_CHECKING

from fastapi import status
from fastapi.responses import JSONResponse

from lnkr import exceptions

if TYPE_CHECKING:
    from fastapi import FastAPI, Request

logger = logging.getLogger(__name__)
NO_STORE_HEADERS = {"Cache-Control": "no-store"}


async def _frontend_api_key_invalid_handler(
    _request: Request,
    error: exceptions.FrontendApiKeyInvalidError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": [{"msg": str(error), "type": "frontend_api_key_invalid"}]},
    )


async def _cursor_invalid_handler(_request: Request, error: exceptions.CursorInvalidError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "detail": [{"input": error.cursor, "loc": ["query", "cursor"], "msg": str(error), "type": "cursor_invalid"}]
        },
    )


async def _login_token_invalid_handler(_request: Request, error: exceptions.LoginTokenInvalidError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": [{"msg": str(error), "type": "login_token_invalid"}]},
    )


async def _login_token_generation_failed_handler(
    _request: Request,
    error: exceptions.LoginTokenGenerationFailedError,
) -> JSONResponse:
    logger.error("Login token generation attempts exhausted")
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": [{"msg": str(error), "type": "login_token_generation_failed"}]},
    )


async def _login_token_delivery_failed_handler(
    _request: Request, error: exceptions.LoginTokenDeliveryFailedError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": [{"msg": str(error), "type": "login_token_delivery_failed"}]},
        headers=NO_STORE_HEADERS | {"Retry-After": "60"},
    )


async def _refresh_token_invalid_handler(_request: Request, error: exceptions.RefreshTokenInvalidError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": [{"msg": str(error), "type": "refresh_token_invalid"}]},
    )


async def _refresh_token_generation_failed_handler(
    _request: Request,
    error: exceptions.RefreshTokenGenerationFailedError,
) -> JSONResponse:
    logger.error("Refresh token generation attempts exhausted")
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": [{"msg": str(error), "type": "refresh_token_generation_failed"}]},
    )


async def _user_does_not_exist_handler(_request: Request, error: exceptions.UserDoesNotExistError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND, content={"detail": [{"msg": str(error), "type": "user_does_not_exist"}]}
    )


async def _user_link_limit_exceeded_handler(
    _request: Request,
    error: exceptions.UserLinkLimitExceededError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": [{"msg": str(error), "type": "user_link_limit_exceeded"}]},
    )


async def _timezone_invalid_handler(_request: Request, error: exceptions.TimezoneInvalidError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "detail": [
                {"input": error.timezone, "loc": ["query", "timezone"], "msg": str(error), "type": "timezone_invalid"}
            ]
        },
    )


async def _slug_already_exists_handler(_request: Request, error: exceptions.SlugAlreadyExistsError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "detail": [{"input": error.slug, "loc": ["body", "slug"], "msg": str(error), "type": "slug_already_exists"}]
        },
    )


async def _slug_does_not_exist_handler(_request: Request, error: exceptions.SlugDoesNotExistError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "detail": [{"input": error.slug, "loc": ["path", "slug"], "msg": str(error), "type": "slug_does_not_exist"}]
        },
    )


async def _slug_not_owned_by_user_handler(_request: Request, error: exceptions.SlugNotOwnedByUserError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={
            "detail": [
                {"input": error.slug, "loc": ["path", "slug"], "msg": str(error), "type": "slug_not_owned_by_user"}
            ]
        },
    )


async def _random_slug_generation_failed_handler(
    _request: Request, error: exceptions.RandomSlugGenerationFailedError
) -> JSONResponse:
    logger.error("Random slug generation attempts exhausted")
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": [{"msg": str(error), "type": "random_slug_generation_failed"}]},
        headers=NO_STORE_HEADERS,
    )


async def _link_expired_handler(_request: Request, error: exceptions.LinkExpiredError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_410_GONE,
        content={"detail": [{"msg": str(error), "type": "link_expired"}]},
        headers=NO_STORE_HEADERS,
    )


async def _link_password_required_handler(
    _request: Request, error: exceptions.LinkPasswordRequiredError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": [{"msg": str(error), "type": "link_password_required"}]},
        headers=NO_STORE_HEADERS,
    )


async def _link_password_invalid_handler(_request: Request, error: exceptions.LinkPasswordInvalidError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": [{"msg": str(error), "type": "link_password_invalid"}]},
        headers=NO_STORE_HEADERS,
    )


async def _link_disabled_handler(_request: Request, error: exceptions.LinkDisabledError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_410_GONE, content={"detail": [{"msg": str(error), "type": "link_disabled"}]}
    )


async def _access_credentials_missing_handler(
    _request: Request, error: exceptions.AccessCredentialsMissingError
) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"detail": str(error)})


async def _access_token_missing_handler(_request: Request, error: exceptions.AccessTokenMissingError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": str(error)})


async def _access_token_invalid_handler(_request: Request, error: exceptions.AccessTokenInvalidError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": str(error)})


async def _access_token_subject_invalid_handler(
    _request: Request,
    error: exceptions.AccessTokenSubjectInvalidError,
) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": str(error)})


def register_exception_handlers(app: FastAPI) -> None:
    """Register only known domain errors; retain FastAPI's default handlers."""
    app.exception_handler(exceptions.FrontendApiKeyInvalidError)(_frontend_api_key_invalid_handler)
    app.exception_handler(exceptions.CursorInvalidError)(_cursor_invalid_handler)
    app.exception_handler(exceptions.LoginTokenInvalidError)(_login_token_invalid_handler)
    app.exception_handler(exceptions.LoginTokenGenerationFailedError)(_login_token_generation_failed_handler)
    app.exception_handler(exceptions.LoginTokenDeliveryFailedError)(_login_token_delivery_failed_handler)
    app.exception_handler(exceptions.RefreshTokenInvalidError)(_refresh_token_invalid_handler)
    app.exception_handler(exceptions.RefreshTokenGenerationFailedError)(_refresh_token_generation_failed_handler)
    app.exception_handler(exceptions.UserDoesNotExistError)(_user_does_not_exist_handler)
    app.exception_handler(exceptions.UserLinkLimitExceededError)(_user_link_limit_exceeded_handler)
    app.exception_handler(exceptions.TimezoneInvalidError)(_timezone_invalid_handler)
    app.exception_handler(exceptions.SlugAlreadyExistsError)(_slug_already_exists_handler)
    app.exception_handler(exceptions.SlugDoesNotExistError)(_slug_does_not_exist_handler)
    app.exception_handler(exceptions.SlugNotOwnedByUserError)(_slug_not_owned_by_user_handler)
    app.exception_handler(exceptions.RandomSlugGenerationFailedError)(_random_slug_generation_failed_handler)
    app.exception_handler(exceptions.LinkExpiredError)(_link_expired_handler)
    app.exception_handler(exceptions.LinkPasswordRequiredError)(_link_password_required_handler)
    app.exception_handler(exceptions.LinkPasswordInvalidError)(_link_password_invalid_handler)
    app.exception_handler(exceptions.LinkDisabledError)(_link_disabled_handler)
    app.exception_handler(exceptions.AccessCredentialsMissingError)(_access_credentials_missing_handler)
    app.exception_handler(exceptions.AccessTokenMissingError)(_access_token_missing_handler)
    app.exception_handler(exceptions.AccessTokenInvalidError)(_access_token_invalid_handler)
    app.exception_handler(exceptions.AccessTokenSubjectInvalidError)(_access_token_subject_invalid_handler)
