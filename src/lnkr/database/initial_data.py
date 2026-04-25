"""
Initial development data for the database.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from lnkr.config.application_settings import ApplicationEnvironment, application_settings
from lnkr.database import AsyncSessionLocal
from lnkr.models import UserCreate
from lnkr.services.user_service import get_or_create_user


async def create_initial_data() -> None:
    """Create initial data in the database."""
    async with AsyncSessionLocal() as session:
        if application_settings.ENVIRONMENT == ApplicationEnvironment.DEVELOPMENT:
            await get_or_create_user(session, UserCreate(email=application_settings.DEVELOPMENT_USER_EMAIL))
