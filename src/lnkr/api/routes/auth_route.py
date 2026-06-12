"""
API endpoints for authentication.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, Response, status
from fastapi.templating import Jinja2Templates

from lnkr.api.dependencies import get_session, verify_frontend_api_key
from lnkr.config.application_settings import application_settings
from lnkr.exceptions import LoginTokenInvalidError, RefreshTokenInvalidError, UserDoesNotExistError
from lnkr.models import (
    AuthTokensRead,
    LoginTokenCreate,
    LoginTokenVerify,
    RefreshTokenRevoke,
    RefreshTokenRotate,
    UserCreate,
)
from lnkr.services.email_service import send_email
from lnkr.services.tokens.access_token_service import create_access_token
from lnkr.services.tokens.login_token_service import consume_login_token, create_and_save_login_token
from lnkr.services.tokens.refresh_token_service import (
    create_and_save_refresh_token,
    revoke_refresh_token,
    rotate_refresh_token,
)
from lnkr.services.user_service import get_or_create_user, get_user_by_id

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

email_templates = Jinja2Templates(directory="templates/email")


router = APIRouter(prefix=application_settings.AUTH_PREFIX, dependencies=[Depends(verify_frontend_api_key)])


@router.post("/request-login-token", status_code=status.HTTP_204_NO_CONTENT)
async def request_login_token_endpoint(
    login_token_create: LoginTokenCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    """Request a login token that is sent to the user's email."""
    login_token_value = await create_and_save_login_token(session, login_token_create)

    message = _create_login_token_email(login_token_create.email, login_token_value)
    # TODO: Add try-except logic and stricter rate limiting.
    await send_email(message)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/verify-login-token")
async def verify_login_token_endpoint(
    login_token_verify: LoginTokenVerify,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AuthTokensRead:
    """Verify login token and return authentication tokens."""
    try:
        login_token = await consume_login_token(session, login_token_verify.login_token_value)
    except LoginTokenInvalidError as login_token_invalid_error:
        login_token_invalid_error.raise_http_exception()

    user = await get_or_create_user(session, UserCreate(email=login_token.email))
    access_token = create_access_token(user_id=user.id)
    refresh_token = await create_and_save_refresh_token(session, user.id)
    return AuthTokensRead(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh-auth-tokens")
async def refresh_auth_tokens_endpoint(
    refresh_token_rotate: RefreshTokenRotate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AuthTokensRead:
    """Verify refresh token and return new authentication tokens."""
    try:
        user_id, new_refresh_token = await rotate_refresh_token(session, refresh_token_rotate.refresh_token_value)
        user = await get_user_by_id(session, user_id)
    except RefreshTokenInvalidError as refresh_token_invalid_error:
        refresh_token_invalid_error.raise_http_exception()
    except UserDoesNotExistError as user_does_not_exist_error:
        user_does_not_exist_error.raise_http_exception()

    access_token = create_access_token(user.id)
    return AuthTokensRead(access_token=access_token, refresh_token=new_refresh_token)


@router.post("/revoke-refresh-token", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_refresh_token_endpoint(
    refresh_token_revoke: RefreshTokenRevoke,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    """Revoke a refresh token and invalidate the current session."""
    try:
        await revoke_refresh_token(session, refresh_token_revoke.refresh_token_value)
    except RefreshTokenInvalidError as refresh_token_invalid_error:
        refresh_token_invalid_error.raise_http_exception()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _create_login_token_email(to_address: str, token: str) -> MIMEMultipart:
    message = MIMEMultipart()
    message["From"] = application_settings.FROM_EMAIL
    message["To"] = to_address
    message["Subject"] = "Email Verification - lnkr"

    message_body = email_templates.get_template("login_token.html.j2").render(
        expiry_time=application_settings.LOGIN_TOKEN_EXPIRE_MINUTES,
        token=token,
        # TODO: Add callback URL to request login token endpoint and attach to login_url.
        # TODO: Use urllib.parse.quote to encode the token value in the URL.
        login_url=f"{application_settings.FRONTEND_APP_URL}/login/verify?login_token_value={token}",
    )
    message.attach(MIMEText(message_body, "html"))
    return message
