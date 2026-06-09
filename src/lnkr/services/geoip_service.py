"""
High level services for geoip management.

@author "Daniel Mizsak" <daniel@mizsak.com>
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
