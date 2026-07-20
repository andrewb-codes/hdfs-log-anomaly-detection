from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from hdfs_anomaly.app.api import deps
from hdfs_anomaly.app.api.v1.admin_profiles import router as admin_router
from hdfs_anomaly.app.api.v1.auth import router as auth_router
from hdfs_anomaly.app.api.v1.history import router as history_router
from hdfs_anomaly.app.api.v1.model import router as model_router
from hdfs_anomaly.app.api.v1.profile import router as profile_router
from hdfs_anomaly.app.api.v1.registration import router as registration_router
from hdfs_anomaly.app.core.config import settings
from hdfs_anomaly.app.core.exceptions import AppError
from hdfs_anomaly.app.core.logging import configure_logging
from hdfs_anomaly.app.middleware.request_logging import request_logging_middleware
from hdfs_anomaly.app.model.resources import load_resources
from hdfs_anomaly.app.rate_limit.service import RateLimitService

configure_logging(settings)
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("application_starting")

    logger.info("loading_resources")
    deps.resources = load_resources()
    logger.info("resources_loaded")

    rate_limiter = RateLimitService.from_settings(settings)

    if rate_limiter.enabled and not await rate_limiter.check_storage():
        logger.error("rate_limit_storage_unavailable")
        raise RuntimeError("Rate limit Redis storage is not available")

    app.state.rate_limiter = rate_limiter
    logger.info("application_started")

    try:
        yield
    finally:
        logger.info("application_stopping")
        deps.resources = None
        app.state.rate_limiter = None
        logger.info("application_stopped")


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "REST API for HDFS Log Anomaly Detection Inference: "
        "authentication, profiles, predict, history, stats and admin profile management."
    ),
    lifespan=lifespan,
)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.middleware("http")(request_logging_middleware)

app.include_router(admin_router)
app.include_router(auth_router)
app.include_router(history_router)
app.include_router(model_router)
app.include_router(profile_router)
app.include_router(registration_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model_loaded": deps.resources is not None}


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    headers = None

    if hasattr(exc, "retry_after"):
        headers = {"Retry-After": str(exc.retry_after)}

    return JSONResponse(
        status_code=exc.status_code, content={"detail": exc.detail}, headers=headers
    )
