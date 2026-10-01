"""
Tests for the geoip service.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING

import pytest

from lnkr.services.geoip_service import get_country_code_from_ip, get_country_flag_from_country_code

if TYPE_CHECKING:
    from geoip2.database import Reader


def test_get_country_code_from_ip__public_ip(
    geoip_reader: Reader,
    ip_address_public: str,
    ip_address_public_country_code: str,
) -> None:
    country_code = get_country_code_from_ip(geoip_reader, ip_address_public)

    assert country_code == ip_address_public_country_code


def test_get_country_code_from_ip__private_ip(geoip_reader: Reader, ip_address_private: str) -> None:
    # A valid address that is not in the database resolves to no country.
    country_code = get_country_code_from_ip(geoip_reader, ip_address_private)

    assert country_code is None


def test_get_country_code_from_ip__malformed_ip(geoip_reader: Reader, ip_address_malformed: str) -> None:
    country_code = get_country_code_from_ip(geoip_reader, ip_address_malformed)

    assert country_code is None


def test_get_country_code_from_ip__missing_ip(geoip_reader: Reader) -> None:
    country_code = get_country_code_from_ip(geoip_reader, None)

    assert country_code is None


def test_get_country_code_from_ip__empty_string(geoip_reader: Reader) -> None:
    country_code = get_country_code_from_ip(geoip_reader, "")

    assert country_code is None


def test_get_country_code_from_ip__geoip_database_unavailable(ip_address_public: str) -> None:
    country_code = get_country_code_from_ip(None, ip_address_public)

    assert country_code is None


@pytest.mark.parametrize(
    ("country_code", "country_flag"),
    [
        ("US", "🇺🇸"),
        ("dk", "🇩🇰"),
        ("ZZ", "🇿🇿"),  # Valid format, but no assigned Unicode flag.
        (None, None),
        ("", None),
        ("USA", None),
        ("1A", None),
        ("ÆØ", None),
    ],
)
def test_get_country_flag_from_country_code__valid_and_invalid_country_codes(
    country_code: str | None,
    country_flag: str | None,
) -> None:
    flag = get_country_flag_from_country_code(country_code)

    assert flag == country_flag
