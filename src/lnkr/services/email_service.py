"""
High level services for email management.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

import random
import smtplib
import socket
from typing import TYPE_CHECKING

from anyio import sleep, to_thread

from lnkr.config.application_settings import ApplicationEnvironment, application_settings

if TYPE_CHECKING:
    from email.mime.multipart import MIMEMultipart


SMTP_TEMPORARY_ERROR_MIN = 400
SMTP_PERMANENT_ERROR_MIN = 500


async def send_email(message: MIMEMultipart) -> None:
    """Send an email with bounded retries without blocking the event loop."""
    # Freeze generated MIME boundaries before smtplib serializes a copy on each attempt.
    message.as_bytes()

    maximum_email_sending_attempts = 3
    for attempt in range(maximum_email_sending_attempts):
        try:
            await to_thread.run_sync(_send_email_sync, message)
        except OSError as error:
            # SMTPException also inherits from OSError.
            if attempt == maximum_email_sending_attempts - 1 or not _is_retryable_smtp_error(error):
                raise
            jitter = random.uniform(0, 0.5)  # noqa: S311 - Retry jitter does not require cryptographic randomness.
            await sleep(2**attempt + jitter)
        else:
            return


def _is_retryable_smtp_error(error: OSError) -> bool:
    """Identify temporary SMTP responses and transient connection failures.

    SMTP reply classes: https://www.rfc-editor.org/rfc/rfc5321#section-4.2.1
    Python exceptions: https://docs.python.org/3.14/library/smtplib.html#smtplib.SMTPException
    """
    match error:
        case smtplib.SMTPResponseException(smtp_code=code):
            # SMTP 4xx replies are temporary; 5xx replies require a change before retrying.
            return SMTP_TEMPORARY_ERROR_MIN <= code < SMTP_PERMANENT_ERROR_MIN
        case smtplib.SMTPRecipientsRefused(recipients=recipients):
            # All recipients were rejected; retry the whole email only if every rejection is temporary.
            return bool(recipients) and all(
                SMTP_TEMPORARY_ERROR_MIN <= code < SMTP_PERMANENT_ERROR_MIN for code, _ in recipients.values()
            )
        case smtplib.SMTPServerDisconnected() | ConnectionError() | TimeoutError():
            # Acceptance may be uncertain; send_email reuses the idempotency key to prevent duplicates.
            # https://resend.com/docs/send-with-smtp#idempotency-key
            return True
        case socket.gaierror(errno=error_number):
            # Retry temporary DNS lookup failures, but not permanent failures such as an unknown hostname.
            return error_number == socket.EAI_AGAIN
        case _:
            # Retry only the cases above; TLS and unrecognized errors fail immediately.
            return False


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
