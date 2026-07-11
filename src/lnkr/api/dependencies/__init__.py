"""
FastAPI dependencies.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from lnkr.api.dependencies.auth import get_current_user
from lnkr.api.dependencies.cache import get_cache
from lnkr.api.dependencies.database import get_session
from lnkr.api.dependencies.geoip import get_geoip_reader
from lnkr.api.dependencies.header import check_frontend_api_key, get_ip_address, get_user_agent, verify_frontend_api_key
from lnkr.api.dependencies.pagination import get_click_cursor
from lnkr.api.dependencies.timezone import get_timezone

__all__ = [
    "check_frontend_api_key",
    "get_cache",
    "get_click_cursor",
    "get_current_user",
    "get_geoip_reader",
    "get_ip_address",
    "get_session",
    "get_timezone",
    "get_user_agent",
    "verify_frontend_api_key",
]
