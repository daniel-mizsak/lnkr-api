"""
API endpoints for health check.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

import logging
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from lnkr.api.dependencies import get_cache, get_session
from lnkr.config.application_settings import application_settings

if TYPE_CHECKING:
    from redis.asyncio import Redis
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
async def health_check_endpoint(
    session: Annotated[AsyncSession, Depends(get_session)],
    cache: Annotated[Redis, Depends(get_cache)],
) -> JSONResponse:
    """Health check endpoint to verify the API is running."""
    try:
        await session.execute(text("SELECT 1"))
    except OperationalError:
        logger.exception("database.health_query_failed")
        return JSONResponse(
            content={"message": "Database connection failed"},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    try:
        cache_status = await cache.ping()
    except RedisError:
        logger.exception("redis.health_ping_failed")
        cache_status = False
    else:
        if not cache_status:
            logger.error("redis.health_ping_failed")

    if not cache_status:
        return JSONResponse(
            content={"message": "Cache connection failed"},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return JSONResponse(
        content={
            "message": "lnkr api running",
            "environment": application_settings.ENVIRONMENT,
            "database": True,
            "cache": True,
        },
        status_code=status.HTTP_200_OK,
        media_type="application/json",
    )
