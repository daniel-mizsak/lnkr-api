"""
High level services for email management.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

import smtplib
from typing import TYPE_CHECKING

from anyio import to_thread

from lnkr.config.application_settings import ApplicationEnvironment, application_settings

if TYPE_CHECKING:
    from email.mime.multipart import MIMEMultipart


async def send_email(message: MIMEMultipart) -> None:
    """Send an email without blocking the event loop."""
    await to_thread.run_sync(_send_email_sync, message)


def _send_email_sync(message: MIMEMultipart) -> None:
    """Send an email using a blocking SMTP client."""
    timeout = 10

    if application_settings.ENVIRONMENT == ApplicationEnvironment.DEVELOPMENT:
        with smtplib.SMTP(
            host=application_settings.SMTP_HOST, port=application_settings.SMTP_PORT, timeout=timeout
        ) as smtp_server:
            smtp_server.login(application_settings.SMTP_USER, application_settings.SMTP_PASSWORD.get_secret_value())
            smtp_server.send_message(message)
    else:
        with smtplib.SMTP_SSL(
            host=application_settings.SMTP_HOST, port=application_settings.SMTP_PORT, timeout=timeout
        ) as smtp_server:
            smtp_server.login(application_settings.SMTP_USER, application_settings.SMTP_PASSWORD.get_secret_value())
            smtp_server.send_message(message)
