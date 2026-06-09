"""
Tests for the geoip service.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING

from lnkr.services.geoip_service import get_country_code_from_ip

if TYPE_CHECKING:
    from geoip2.database import Reader


def test_get_country_code_from_ip__public_ip(
    geoip_reader: Reader,
    ip_address_public: str,
    ip_address_public_country_code: str,
) -> None:
    assert get_country_code_from_ip(geoip_reader, ip_address_public) == ip_address_public_country_code


def test_get_country_code_from_ip__private_ip(geoip_reader: Reader, ip_address_private: str) -> None:
    # A valid address that is not in the database resolves to no country.
    assert get_country_code_from_ip(geoip_reader, ip_address_private) is None


def test_get_country_code_from_ip__malformed_ip(geoip_reader: Reader, ip_address_malformed: str) -> None:
    assert get_country_code_from_ip(geoip_reader, ip_address_malformed) is None


def test_get_country_code_from_ip__none(geoip_reader: Reader) -> None:
    assert get_country_code_from_ip(geoip_reader, None) is None


def test_get_country_code_from_ip__empty_string(geoip_reader: Reader) -> None:
    assert get_country_code_from_ip(geoip_reader, "") is None
