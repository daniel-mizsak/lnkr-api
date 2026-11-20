"""
Tests for application logging configuration.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

import logging
from typing import TYPE_CHECKING

from lnkr.logging_config import configure_logging

if TYPE_CHECKING:
    import pytest


def test_configure_logging__repeated_calls_do_not_duplicate_output(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Named loggers propagate messages to the root logger's handlers by default.
    root_logger = logging.getLogger()
    # Remove pytest's handlers so basicConfig configures logging. Monkeypatch restores them after the test.
    monkeypatch.setattr(root_logger, "handlers", [])
    # Start at WARNING to verify configuration enables INFO. Monkeypatch restores the original level.
    monkeypatch.setattr(root_logger, "level", logging.WARNING)

    configure_logging()
    # Reconfiguring must not add another handler or emit the same message twice.
    configure_logging()
    logging.getLogger("lnkr.logging_config_test").info("Login succeeded for user %s", "user-id")
    output = capsys.readouterr().err

    assert len(root_logger.handlers) == 1
    assert "INFO lnkr.logging_config_test: Login succeeded for user user-id" in output
    assert len(output.splitlines()) == 1


def test_configure_logging__existing_handlers_preserved(monkeypatch: pytest.MonkeyPatch) -> None:
    root_logger = logging.getLogger()
    handler = logging.NullHandler()
    monkeypatch.setattr(root_logger, "handlers", [handler])
    monkeypatch.setattr(root_logger, "level", logging.WARNING)

    configure_logging()

    assert root_logger.handlers == [handler]
    assert root_logger.level == logging.WARNING
