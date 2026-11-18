"""
Tests for the timezone dependency.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

import pytest

from lnkr.api.dependencies.timezone import get_timezone
from lnkr.exceptions import TimezoneInvalidError


def test_get_timezone__defaults_to_utc() -> None:
    timezone = get_timezone()

    assert timezone.key == "UTC"


def test_get_timezone__valid_iana_timezone() -> None:
    timezone = get_timezone("Europe/Copenhagen")

    assert timezone.key == "Europe/Copenhagen"


def test_get_timezone__invalid_timezone() -> None:
    timezone = "Not/A-Timezone"

    with pytest.raises(TimezoneInvalidError) as exc_info:
        get_timezone(timezone)

    assert exc_info.value.timezone == timezone
