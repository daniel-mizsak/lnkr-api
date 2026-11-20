"""
Application logging configuration.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

import logging


def configure_logging() -> None:
    """Configure console logging without replacing existing handlers."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
