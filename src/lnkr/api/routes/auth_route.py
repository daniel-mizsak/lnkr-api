"""
API endpoints for authentication.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, Response, status
from fastapi.templating import Jinja2Templates

from lnkr.api.dependencies import get_session
from lnkr.config import settings
from lnkr.exceptions import LoginTokenInvalidError
from lnkr.models import AccessTokenRead, LoginTokenCreate
from lnkr.services.access_token_service import create_access_token
from lnkr.services.email_service import send_email
from lnkr.services.login_token_service import (
    create_and_save_login_token,
    mark_login_token_as_used,
    validate_login_token,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

email_templates = Jinja2Templates(directory="templates/email")


router = APIRouter(prefix=settings.AUTH_PREFIX)


@router.post("/request-login-token")
async def request_login_token_endpoint(
    login_token_create: LoginTokenCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    """Request a login token that is sent to the user's email."""
    login_token_value = await create_and_save_login_token(session, login_token_create)

    message = _create_login_token_email(login_token_create.email, login_token_value)
    await send_email(message)
    return Response(status_code=status.HTTP_200_OK)


@router.get("/verify-login-token")
async def verify_login_token_endpoint(
    login_token_value: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AccessTokenRead:
    """Verify login token and return access token."""
    try:
        login_token = await validate_login_token(session, login_token_value)
    except LoginTokenInvalidError as login_token_invalid_error:
        login_token_invalid_error.raise_http_exception()
    await mark_login_token_as_used(session, login_token)

    access_token = create_access_token(email=login_token.email)
    return AccessTokenRead(access_token=access_token)


def _create_login_token_email(to_address: str, token: str) -> MIMEMultipart:
    message = MIMEMultipart()
    message["From"] = settings.FROM_EMAIL
    message["To"] = to_address
    message["Subject"] = "Email Verification - lnkr"

    message_body = email_templates.get_template("login_token.html.j2").render(
        expiry_time=settings.LOGIN_TOKEN_EXPIRE_MINUTES,
        token=token,
        # TODO: Add token url.
        login_url="#",
    )
    message.attach(MIMEText(message_body, "html"))
    return message
