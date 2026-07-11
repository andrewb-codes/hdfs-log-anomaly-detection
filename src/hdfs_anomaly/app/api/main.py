from contextlib import asynccontextmanager

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
from hdfs_anomaly.app.model.resources import load_resources


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Load inference resources on application startup."""
    deps.resources = load_resources()
    try:
        yield
    finally:
        deps.resources = None


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
    description=(
        "REST API for HDFS Log Anomaly Detection Inference: "
        "authentication, profiles, predict, history, stats and admin profile management."
    ),
)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

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
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
