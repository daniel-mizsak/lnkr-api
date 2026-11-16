"""
Fixtures used in testing authentication API routes.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING

import pytest

from lnkr.api.dependencies import verify_frontend_api_key
from lnkr.main import app

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from httpx2 import AsyncClient


@pytest.fixture()
async def override_verify_frontend_api_key(client: AsyncClient) -> AsyncGenerator[None]:  # noqa: ARG001
    # Depend on `client` so this fixture runs after the default override is installed,
    # then pop it so the real dependency runs and raises on the missing header.
    original_frontend_api_key = app.dependency_overrides.pop(verify_frontend_api_key, None)
    yield
    if original_frontend_api_key is not None:
        app.dependency_overrides[verify_frontend_api_key] = original_frontend_api_key
