"""
Tests for the email service.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

import copy
import logging
import smtplib
import socket
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
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
    "send_error",
    [
        pytest.param(smtplib.SMTPDataError(451, b"Try again later"), id="message-rejected"),
        pytest.param(
            smtplib.SMTPRecipientsRefused({"user@example.com": (450, b"Try again later")}),
            id="recipient-unavailable",
        ),
        pytest.param(smtplib.SMTPServerDisconnected("Disconnected"), id="smtp-disconnected"),
        pytest.param(ConnectionRefusedError("Connection refused"), id="connection-refused"),
        pytest.param(TimeoutError("Timed out"), id="timeout"),
        pytest.param(socket.gaierror(socket.EAI_AGAIN, "Temporary DNS failure"), id="temporary-dns-failure"),
    ],
)
async def test_send_email__retries_transient_failure(send_error: OSError, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger=email_service.__name__)
    message = MIMEMultipart()
    run_sync = mock.AsyncMock(side_effect=[send_error, None])
    sleep = mock.AsyncMock()

    with (
        mock.patch.object(email_service.to_thread, "run_sync", run_sync),
        mock.patch.object(email_service, "sleep", sleep),
    ):
        await email_service.send_email(message)

    assert run_sync.await_count == 2
    sleep.assert_awaited_once()
    assert caplog.record_tuples == [(email_service.__name__, logging.WARNING, "email.retrying")]
    assert caplog.records[0].exc_info is not None
    assert caplog.records[0].exc_info[1] is send_error


async def test_send_email__exhausted_sending_attempts(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger=email_service.__name__)
    message = MIMEMultipart()
    send_error = TimeoutError("Timed out")
    run_sync = mock.AsyncMock(side_effect=send_error)
    sleep = mock.AsyncMock()

    with (
        mock.patch.object(email_service.to_thread, "run_sync", run_sync),
        mock.patch.object(email_service, "sleep", sleep),
        mock.patch.object(email_service.random, "uniform", side_effect=[0.25, 0.5]),
        pytest.raises(TimeoutError) as exc_info,
    ):
        await email_service.send_email(message)
    logged_errors = [record.exc_info[1] for record in caplog.records if record.exc_info is not None]

    assert exc_info.value is send_error
    assert run_sync.await_count == 3
    assert sleep.await_args_list == [mock.call(1.25), mock.call(2.5)]  # 1 + 0.25, 2 + 0.5
    assert caplog.record_tuples == [
        (email_service.__name__, logging.WARNING, "email.retrying"),
        (email_service.__name__, logging.WARNING, "email.retrying"),
        (email_service.__name__, logging.ERROR, "email.retries_exhausted"),
    ]
    assert logged_errors == [send_error] * 3


@pytest.mark.parametrize(
    "send_error",
    [
        pytest.param(smtplib.SMTPAuthenticationError(535, b"Invalid credentials"), id="invalid-credentials"),
        pytest.param(
            smtplib.SMTPRecipientsRefused({"user@example.com": (550, b"Unknown recipient")}),
            id="unknown-recipient",
        ),
        pytest.param(ssl.SSLCertVerificationError("Invalid certificate"), id="invalid-certificate"),
        pytest.param(socket.gaierror(socket.EAI_NONAME, "Unknown hostname"), id="unknown-hostname"),
    ],
)
async def test_send_email__does_not_retry_non_retryable_failure(
    send_error: OSError,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger=email_service.__name__)
    message = MIMEMultipart()
    run_sync = mock.AsyncMock(side_effect=send_error)
    sleep = mock.AsyncMock()

    with (
        mock.patch.object(email_service.to_thread, "run_sync", run_sync),
        mock.patch.object(email_service, "sleep", sleep),
        pytest.raises(type(send_error)) as exc_info,
    ):
        await email_service.send_email(message)

    assert exc_info.value is send_error
    run_sync.assert_awaited_once()
    sleep.assert_not_awaited()
    assert caplog.record_tuples == [(email_service.__name__, logging.ERROR, "email.non_retryable_error")]
    assert caplog.records[0].exc_info is not None
    assert caplog.records[0].exc_info[1] is send_error


async def test_send_email__does_not_retry_unexpected_failure(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger=email_service.__name__)
    message = MIMEMultipart()
    send_error = ValueError("Unexpected error")
    run_sync = mock.AsyncMock(side_effect=send_error)
    sleep = mock.AsyncMock()

    with (
        mock.patch.object(email_service.to_thread, "run_sync", run_sync),
        mock.patch.object(email_service, "sleep", sleep),
        pytest.raises(ValueError, match="Unexpected error") as exc_info,
    ):
        await email_service.send_email(message)

    assert exc_info.value is send_error
    run_sync.assert_awaited_once()
    sleep.assert_not_awaited()
    assert caplog.record_tuples == []


async def test_send_email__preserves_message_and_idempotency_key_across_retries() -> None:
    message = MIMEMultipart()
    message["Resend-Idempotency-Key"] = "login-token/test"
    message.attach(MIMEText("Login token: ABC123", "html"))
    payloads: list[bytes] = []
    send = mock.Mock(side_effect=[TimeoutError("Timed out"), None])

    def send_email_sync(message: MIMEMultipart) -> None:
        # Serialize a copy, as smtplib.send_message does, to catch regenerated MIME boundaries.
        payload = copy.copy(message).as_bytes()
        payloads.append(payload)
        send(payload)

    with (
        mock.patch.object(email_service, "_send_email_sync", side_effect=send_email_sync),
        mock.patch.object(email_service, "sleep", mock.AsyncMock()),
    ):
        await email_service.send_email(message)

    assert len(payloads) == 2
    assert payloads[0] == payloads[1]
    assert b"Resend-Idempotency-Key: login-token/test" in payloads[0]


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
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger=email_service.__name__)
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
    assert caplog.record_tuples == [(email_service.__name__, logging.INFO, "email.accepted")]
