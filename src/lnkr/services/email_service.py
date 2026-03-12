"""
Email sending service.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

import asyncio
import smtplib
from typing import TYPE_CHECKING

from lnkr.config import Environment, settings

if TYPE_CHECKING:
    from email.mime.multipart import MIMEMultipart


async def send_email(message: MIMEMultipart) -> None:
    """Send an email without blocking the event loop."""
    await asyncio.to_thread(_send_email_sync, message)


def _send_email_sync(message: MIMEMultipart) -> None:
    """Send an email using a blocking SMTP client."""
    timeout = 10

    if settings.ENVIRONMENT == Environment.DEVELOPMENT:
        with smtplib.SMTP(host=settings.SMTP_HOST, port=settings.SMTP_PORT, timeout=timeout) as smtp_server:
            smtp_server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            smtp_server.send_message(message)
    else:
        with smtplib.SMTP_SSL(host=settings.SMTP_HOST, port=settings.SMTP_PORT, timeout=timeout) as smtp_server:
            smtp_server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            smtp_server.send_message(message)
