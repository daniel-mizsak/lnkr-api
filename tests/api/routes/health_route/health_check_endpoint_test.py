"""
Tests for the health check endpoint.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

import logging
from typing import TYPE_CHECKING
from unittest import mock

from fastapi import status
from redis.exceptions import RedisError
from sqlalchemy.exc import OperationalError

from lnkr.api.dependencies import get_cache
from lnkr.config.application_settings import ApplicationEnvironment
from lnkr.main import app

if TYPE_CHECKING:
    import pytest
    from httpx2 import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession


async def test_health_check__database_failure(
    client: AsyncClient,
    session: AsyncSession,
    caplog: pytest.LogCaptureFixture,
) -> None:
    database_error = OperationalError("SELECT 1", None, OSError("database unavailable"))

    with mock.patch.object(session, "execute", mock.AsyncMock(side_effect=database_error)):
        response = await client.get(url="/health")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    data = response.json()

    assert data == {"message": "Database connection failed"}
    records = [
        record
        for record in caplog.records
        if record.name == "lnkr.api.routes.health_route" and record.getMessage() == "Database health check failed"
    ]
    assert records
    assert records[0].levelno == logging.ERROR
    assert records[0].exc_info
    assert records[0].exc_info[1] is database_error


async def test_health_check__redis_ping_exception(client: AsyncClient, caplog: pytest.LogCaptureFixture) -> None:
    cache_error = RedisError("cache unavailable")
    cache = mock.AsyncMock()
    cache.ping.side_effect = cache_error

    with mock.patch.dict(app.dependency_overrides, {get_cache: lambda: cache}):
        response = await client.get(url="/health")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    data = response.json()

    assert data == {"message": "Cache connection failed"}
    records = [
        record
        for record in caplog.records
        if record.name == "lnkr.api.routes.health_route" and record.getMessage() == "Cache health check failed"
    ]
    assert records
    assert records[0].levelno == logging.ERROR
    assert records[0].exc_info
    assert records[0].exc_info[1] is cache_error


async def test_health_check__redis_ping_false(client: AsyncClient, caplog: pytest.LogCaptureFixture) -> None:
    cache = mock.AsyncMock()
    cache.ping.return_value = False

    with mock.patch.dict(app.dependency_overrides, {get_cache: lambda: cache}):
        response = await client.get(url="/health")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    data = response.json()

    assert data == {"message": "Cache connection failed"}
    assert ("lnkr.api.routes.health_route", logging.ERROR, "Cache health check returned false") in caplog.record_tuples


async def test_health_check__healthy_dependencies(client: AsyncClient) -> None:
    response = await client.get(url="/health")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert data["message"] == "lnkr api running"
    assert data["environment"] == ApplicationEnvironment.DEVELOPMENT
    assert data["database"] is True
    assert data["cache"] is True
