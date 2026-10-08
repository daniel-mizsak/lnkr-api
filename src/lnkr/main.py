"""
Main application.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import geoip2.database
import redis.asyncio as redis
import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from maxminddb import InvalidDatabaseError
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.scrubber import DEFAULT_DENYLIST, EventScrubber
from sqlalchemy.exc import SQLAlchemyError

from lnkr.api.dependencies.header import CLIENT_IP_HEADER, FRONTEND_API_KEY_HEADER
from lnkr.api.main import api_router
from lnkr.config.application_settings import ApplicationEnvironment, application_settings
from lnkr.database import engine
from lnkr.database.initial_data import create_initial_data

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

if (application_settings.SENTRY_DSN is not None) and (
    application_settings.ENVIRONMENT != ApplicationEnvironment.DEVELOPMENT
):
    sentry_sdk.init(
        dsn=application_settings.SENTRY_DSN.get_secret_value(),
        environment=application_settings.ENVIRONMENT,
        disabled_integrations=[LoggingIntegration()],
        send_default_pii=False,
        include_local_variables=False,
        max_request_body_size="never",
        max_breadcrumbs=0,
        event_scrubber=EventScrubber(denylist=[*DEFAULT_DENYLIST, FRONTEND_API_KEY_HEADER, CLIENT_IP_HEADER]),
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Execute before application startup."""
    try:
        await create_initial_data()
    except SQLAlchemyError:
        logger.exception("database.create_initial_data_failed")
        raise
    # TODO: Avoid interpolating Redis credentials into the URL.
    app.state.cache = redis.from_url(
        "redis://"
        f"{application_settings.REDIS_USERNAME}:"
        f"{application_settings.REDIS_PASSWORD.get_secret_value()}@"
        f"{application_settings.REDIS_HOST}:{application_settings.REDIS_PORT}/"
        f"{application_settings.REDIS_DATABASE_APPLICATION}",
        decode_responses=True,
    )
    try:
        app.state.geoip_reader = geoip2.database.Reader(application_settings.GEOIP_COUNTRY_DATABASE_PATH)
    except OSError:
        app.state.geoip_reader = None
        logger.warning("geoip.file_open_failed", exc_info=True)
    except InvalidDatabaseError:
        app.state.geoip_reader = None
        logger.warning("geoip.format_invalid", exc_info=True)

    yield

    if app.state.geoip_reader is not None:
        app.state.geoip_reader.close()
    await app.state.cache.close()
    await engine.dispose()


app = FastAPI(
    title="lnkr",
    description="Link manager REST API.",
    version=application_settings.API_VERSION,
    lifespan=lifespan,
    swagger_ui_parameters={
        "defaultModelsExpandDepth": 0,
        "displayRequestDuration": True,
    },
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
