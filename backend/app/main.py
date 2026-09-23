"""FastAPI application factory."""

from fastapi import FastAPI

from app import __version__
from app.api import admin, athletes, health, jobs, results, sessions, videos
from app.config import get_settings
from app.errors import install_error_handlers
from app.logging import RequestIdMiddleware, configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    app = FastAPI(
        title="PitchLab API",
        version=__version__,
        description="Async video-analysis backend around the pitching timing analyzer.",
    )
    app.add_middleware(RequestIdMiddleware)
    install_error_handlers(app)
    for module in (health, athletes, sessions, videos, jobs, results, admin):
        app.include_router(module.router)
    return app


app = create_app()
