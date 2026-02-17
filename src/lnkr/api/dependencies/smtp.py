"""
FastAPI dependency that provides the SMTP connection.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

import smtplib
from typing import TYPE_CHECKING

from lnkr.config import Environment, settings

if TYPE_CHECKING:
    from collections.abc import Generator


def get_smtp_server() -> Generator[smtplib.SMTP]:
    """Get SMTP server for sending emails."""
    if settings.ENVIRONMENT == Environment.DEVELOPMENT:
        with smtplib.SMTP(host=settings.SMTP_HOST, port=settings.SMTP_PORT) as smtp_server:
            smtp_server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            yield smtp_server

    else:
        with smtplib.SMTP_SSL(host=settings.SMTP_HOST, port=settings.SMTP_PORT) as smtp_server:
            smtp_server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            yield smtp_server
