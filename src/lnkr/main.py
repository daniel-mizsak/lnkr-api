"""
Main application.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import geoip2.database
import redis.asyncio as redis
import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from lnkr.api.main import api_router
from lnkr.config.application_settings import ApplicationEnvironment, application_settings
from lnkr.database import engine
from lnkr.database.initial_data import create_initial_data

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

if (application_settings.SENTRY_DSN is not None) and (
    application_settings.ENVIRONMENT != ApplicationEnvironment.DEVELOPMENT
):
    sentry_sdk.init(
        dsn=application_settings.SENTRY_DSN.get_secret_value(),
        environment=application_settings.ENVIRONMENT,
        send_default_pii=True,
        traces_sample_rate=1.0,
        profile_session_sample_rate=1.0,
        profile_lifecycle="trace",
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Execute before application startup."""
    await create_initial_data()
    # TODO: Avoid interpolating Redis credentials into the URL.
    app.state.cache = redis.from_url(
        "redis://"
        f"{application_settings.REDIS_USERNAME}:"
        f"{application_settings.REDIS_PASSWORD.get_secret_value()}@"
        f"{application_settings.REDIS_HOST}:{application_settings.REDIS_PORT}/"
        f"{application_settings.REDIS_DATABASE_APPLICATION}",
        decode_responses=True,
    )
    # TODO: Do not fail app startup if the GeoIP database is not available.
    app.state.geoip_reader = geoip2.database.Reader(application_settings.GEOIP_COUNTRY_DATABASE_PATH)

    yield

    app.state.geoip_reader.close()
    await app.state.cache.close()
    await engine.dispose()


app = FastAPI(
    title="lnkr", description="Link manager REST API.", version=application_settings.API_VERSION, lifespan=lifespan
)


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    """Redirect to API documentation."""
    return RedirectResponse(url="/docs")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"]
    if application_settings.ENVIRONMENT == ApplicationEnvironment.DEVELOPMENT
    else [application_settings.FRONTEND_APP_URL, application_settings.FRONTEND_FORWARD_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(api_router)
