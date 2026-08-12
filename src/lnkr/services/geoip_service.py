"""
High level services for geoip management.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING

from geoip2.errors import AddressNotFoundError

if TYPE_CHECKING:
    from geoip2.database import Reader


def get_country_code_from_ip(reader: Reader, ip_address: str | None) -> str | None:
    """Get the country code for a given IP address."""
    if not ip_address:
        return None
    try:
        return reader.country(ip_address).country.iso_code
    except AddressNotFoundError, ValueError:
        return None


def get_country_flag_from_country_code(country_code: str | None) -> str | None:
    """Convert an ISO alpha-2 country code to its flag emoji."""
    country_code_length = 2
    if (
        not country_code
        or len(country_code) != country_code_length
        or not country_code.isascii()
        or not country_code.isalpha()
    ):
        return None

    regional_indicator_offset = 127397
    return "".join(chr(ord(character) + regional_indicator_offset) for character in country_code.upper())
