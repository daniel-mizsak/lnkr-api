"""
Tests for the email service boundary.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from email.mime.multipart import MIMEMultipart
from unittest import mock

import pytest

from lnkr.config.application_settings import ApplicationEnvironment, application_settings
from lnkr.services import email_service


async def test_send_email__offloads_blocking_smtp_call() -> None:
    message = MIMEMultipart()
    run_sync = mock.AsyncMock()
    with mock.patch.object(email_service.to_thread, "run_sync", run_sync):
        await email_service.send_email(message)

    run_sync.assert_awaited_once_with(email_service._send_email_sync, message)  # noqa: SLF001


@pytest.mark.parametrize(
    ("environment", "smtp_client_name"),
    [
        (ApplicationEnvironment.DEVELOPMENT, "SMTP"),
        (ApplicationEnvironment.PRODUCTION, "SMTP_SSL"),
    ],
)
def test_send_email_sync__uses_environment_specific_smtp_client(
    environment: ApplicationEnvironment,
    smtp_client_name: str,
) -> None:
    message = MIMEMultipart()
    smtp_client = mock.MagicMock()
    smtp_server = smtp_client.return_value.__enter__.return_value
    with (
        mock.patch.object(application_settings, "ENVIRONMENT", environment),
        mock.patch.object(email_service.smtplib, smtp_client_name, smtp_client),
    ):
        email_service._send_email_sync(message)  # noqa: SLF001

    smtp_client.assert_called_once_with(
        host=application_settings.SMTP_HOST,
        port=application_settings.SMTP_PORT,
        timeout=10,
    )
    smtp_server.login.assert_called_once_with(
        application_settings.SMTP_USER,
        application_settings.SMTP_PASSWORD.get_secret_value(),
    )
    smtp_server.send_message.assert_called_once_with(message)
