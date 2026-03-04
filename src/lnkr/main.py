"""
Main application.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import redis
import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from lnkr.api.main import api_router
from lnkr.config import Environment, settings
from lnkr.database import create_database, engine

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

if (settings.SENTRY_DSN is not None) and (settings.ENVIRONMENT != Environment.DEVELOPMENT):
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        send_default_pii=True,
        traces_sample_rate=1.0,
        profile_session_sample_rate=1.0,
        profile_lifecycle="trace",
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Execute before application startup."""
    create_database()
    app.state.cache = redis.from_url(settings.REDIS_URL, decode_responses=True)
    yield
    app.state.cache.close()
    engine.dispose()


app = FastAPI(title="lnkr", description="Link manager REST API.", version=settings.API_VERSION, lifespan=lifespan)


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    """Redirect to API documentation."""
    return RedirectResponse(url="/docs")


app.add_middleware(
    CORSMiddleware,  # ty:ignore[invalid-argument-type]
    allow_origins=["*"]
    if settings.ENVIRONMENT == Environment.DEVELOPMENT
    else [settings.FRONTEND_APP_URL, settings.FRONTEND_FORWARD_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(api_router)
