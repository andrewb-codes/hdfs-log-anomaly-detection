import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException
from sqlalchemy.orm import Session

from hdfs_anomaly.api.database import SessionLocal, init_db
from hdfs_anomaly.api.history import clear_history, list_history, request_stats, save_history_item
from hdfs_anomaly.api.inference import run_inference
from hdfs_anomaly.api.resources import InferenceResources, load_resources
from hdfs_anomaly.api.schemas import (
    ForwardRequest,
    ForwardResponse,
    ModelInfoResponse,
    HistoryItem,
    StatsResponse,
    DeleteHistoryResponse
)

DELETE_HISTORY_TOKEN = "delete-history-token"

resources: InferenceResources | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database tables and inference resources on application startup."""
    global resources
    init_db()
    resources = load_resources()
    yield


app = FastAPI(title="HDFS Log Anomaly Detection API", lifespan=lifespan)


def get_db():
    """Provide a database session for one request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_resources() -> InferenceResources:
    """Return loaded inference resources or fail if startup loading did not complete."""
    if resources is None:
        raise RuntimeError("inference resources are not loaded")
    return resources


@app.get("/health")
def health() -> dict:
    """Return service health and model loading status."""
    return {
        "status": "ok",
        "model_loaded": resources is not None
    }


@app.get("/model-info", response_model=ModelInfoResponse)
def model_info(inference_resources: InferenceResources = Depends(get_resources)) -> ModelInfoResponse:
    """Return metadata for the currently loaded inference model."""
    return ModelInfoResponse(
        model_type="many_to_many_lstm",
        scoring_strategy=inference_resources.scoring_strategy,
        threshold=inference_resources.threshold,
        window_size=inference_resources.window_size,
        stride=inference_resources.stride,
        device=inference_resources.device
    )


@app.post("/forward", response_model=ForwardResponse)
def forward(
        request: ForwardRequest,
        db: Session = Depends(get_db),
        inference_resources: InferenceResources = Depends(get_resources)
) -> ForwardResponse:
    """Run anomaly inference for raw HDFS log lines and store request history."""
    started_at = time.perf_counter()

    try:
        response = run_inference(request, inference_resources)
    except Exception:
        processing_ms = (time.perf_counter() - started_at) * 1000
        save_history_item(
            db,
            block_id=request.block_id,
            status_code=403,
            processing_ms=processing_ms,
            num_log_lines=len(request.log_lines),
            error_message="model couldn't process data",
        )
        raise HTTPException(status_code=403, detail="model couldn`t process data")

    processing_ms = (time.perf_counter() - started_at) * 1000
    save_history_item(
        db,
        block_id=response.block_id,
        status_code=200,
        processing_ms=processing_ms,
        num_log_lines=response.num_log_lines,
        num_events=response.num_events,
        num_windows=response.num_windows,
        score=response.score,
        threshold=response.threshold,
        is_anomaly=response.is_anomaly,
    )
    return response


@app.get("/history", response_model=list[HistoryItem])
def history(db: Session = Depends(get_db)) -> list[HistoryItem]:
    """Return stored forward request history."""
    return list_history(db)


@app.delete("/history", response_model=DeleteHistoryResponse)
def delete_history(
        x_delete_token: str | None = Header(default=None),
        db: Session = Depends(get_db)
) -> DeleteHistoryResponse:
    """Delete stored request history when the confirmation token is valid."""
    if x_delete_token != DELETE_HISTORY_TOKEN:
        raise HTTPException(status_code=403, detail="invalid delete token")

    deleted = clear_history(db)
    return DeleteHistoryResponse(deleted=deleted)


@app.get("/stats", response_model=StatsResponse)
def stats(db: Session = Depends(get_db)) -> StatsResponse:
    """Return aggregate request processing statistics."""
    return StatsResponse(**request_stats(db))
