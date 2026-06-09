"""
FastAPI dependencies.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from lnkr.api.dependencies.auth import get_current_user
from lnkr.api.dependencies.cache import get_cache
from lnkr.api.dependencies.database import get_session
from lnkr.api.dependencies.frontend import check_frontend_api_key, verify_frontend_api_key
from lnkr.api.dependencies.geoip import get_geoip_reader

__all__ = [
    "check_frontend_api_key",
    "get_cache",
    "get_current_user",
    "get_geoip_reader",
    "get_session",
    "verify_frontend_api_key",
]
