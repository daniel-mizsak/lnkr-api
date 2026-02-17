"""
Main module for the routes.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

from fastapi import APIRouter

from lnkr.api.routes import auth_route, click_route, forward_route, health_route, link_route
from lnkr.config import settings

api_router = APIRouter()

api_router.include_router(health_route.router, prefix=settings.API_VERSION_PREFIX, tags=["health"])
api_router.include_router(auth_route.router, prefix=settings.API_VERSION_PREFIX, tags=["auth"])
api_router.include_router(link_route.router, prefix=settings.API_VERSION_PREFIX, tags=["link"])
api_router.include_router(click_route.router, prefix=settings.API_VERSION_PREFIX, tags=["click"])
api_router.include_router(forward_route.router, prefix=settings.API_VERSION_PREFIX, tags=["forward"])
