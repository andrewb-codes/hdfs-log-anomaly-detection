from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

NotEmptyStrippedString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ForwardRequest(BaseModel):
    block_id: NotEmptyStrippedString
    log_lines: list[NotEmptyStrippedString] = Field(..., min_length=1)
    return_event_ids: bool = False
    return_window_scores: bool = False


class ForwardResponse(BaseModel):
    block_id: str
    score: float
    threshold: float
    is_anomaly: bool
    scoring_strategy: str
    num_log_lines: int
    num_events: int
    num_windows: int
    event_ids: list[int] | None = None
    window_scores: list[float] | None = None


class HistoryItem(BaseModel):
    id: int
    created_at: datetime
    block_id: str | None
    status_code: int
    processing_ms: float
    num_log_lines: int | None
    num_events: int | None
    num_windows: int | None
    score: float | None
    threshold: float | None
    is_anomaly: bool | None
    error_message: str | None

    model_config = {"from_attributes": True}


class StatsResponse(BaseModel):
    total_requests: int
    successful_requests: int
    failed_requests: int

    mean_processing_ms: float | None
    p50_processing_ms: float | None
    p95_processing_ms: float | None
    p99_processing_ms: float | None

    mean_num_log_lines: float | None
    min_num_log_lines: int | None
    max_num_log_lines: int | None


class DeleteHistoryResponse(BaseModel):
    deleted: int


class ModelInfoResponse(BaseModel):
    model_type: str
    scoring_strategy: str
    threshold: float
    window_size: int
    stride: int
    device: str


class TokenRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
