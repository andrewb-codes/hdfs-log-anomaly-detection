from datetime import datetime

from pydantic import BaseModel


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


class HistoryListResponse(BaseModel):
    items: list[HistoryItem]
    has_next: bool


class DeleteHistoryResponse(BaseModel):
    deleted: int


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
