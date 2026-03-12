"""
FastAPI dependencies.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

from lnkr.api.dependencies.auth import get_current_user
from lnkr.api.dependencies.cache import get_cache
from lnkr.api.dependencies.database import get_session

__all__ = [
    "get_cache",
    "get_current_user",
    "get_session",
]
