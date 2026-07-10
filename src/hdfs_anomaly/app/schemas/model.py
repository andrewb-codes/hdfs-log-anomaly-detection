from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

NotEmptyStrippedString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class PredictRequest(BaseModel):
    block_id: NotEmptyStrippedString
    log_lines: list[NotEmptyStrippedString] = Field(..., min_length=1)
    return_event_ids: bool = False
    return_window_scores: bool = False


class PredictResponse(BaseModel):
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


class ModelInfoResponse(BaseModel):
    model_type: str
    scoring_strategy: str
    threshold: float
    window_size: int
    stride: int
    device: str
