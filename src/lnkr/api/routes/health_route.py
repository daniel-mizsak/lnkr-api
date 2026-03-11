"""
API endpoints for health check.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from lnkr.api.dependencies import get_cache, get_session
from lnkr.config import settings

if TYPE_CHECKING:
    from redis import Redis
    from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/health")
def health_check_endpoint(
    session: Annotated[Session, Depends(get_session)],
    cache: Annotated[Redis, Depends(get_cache)],
) -> JSONResponse:
    """Health check endpoint to verify the API is running."""
    try:
        session.execute(text("SELECT 1"))
    except OperationalError:
        return JSONResponse(
            content={"message": "Database connection failed"},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    try:
        cache_status = cache.ping()
    except RedisError:
        cache_status = False

    if not cache_status:
        return JSONResponse(
            content={"message": "Cache connection failed"},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return JSONResponse(
        content={
            "message": "lnkr api running",
            "environment": settings.ENVIRONMENT,
            "database": True,
            "cache": True,
        },
        status_code=status.HTTP_200_OK,
        media_type="application/json",
    )
