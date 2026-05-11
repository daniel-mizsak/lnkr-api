"""
Fixtures used in testing forward api routes.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING

import pytest

from lnkr.api.dependencies import check_frontend_api_key
from lnkr.main import app

if TYPE_CHECKING:
    from collections.abc import Generator

    from fastapi.testclient import TestClient


@pytest.fixture()
def override_check_frontend_api_key(client: TestClient) -> Generator[None]:  # noqa: ARG001
    # Depend on `client` so fixture runs after the default override is installed.
    original_frontend_request = app.dependency_overrides.get(check_frontend_api_key)
    app.dependency_overrides[check_frontend_api_key] = lambda: False
    yield
    if original_frontend_request is not None:
        app.dependency_overrides[check_frontend_api_key] = original_frontend_request
