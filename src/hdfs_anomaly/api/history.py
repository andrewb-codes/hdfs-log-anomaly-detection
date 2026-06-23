from datetime import UTC, datetime

import numpy as np
from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, Session, mapped_column

from hdfs_anomaly.api.database import Base


def utc_now() -> datetime:
    """Return the current UTC timestamp for history records."""
    return datetime.now(UTC)


class RequestHistory(Base):
    __tablename__ = "request_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    block_id: Mapped[str | None] = mapped_column(String, nullable=True)
    status_code: Mapped[int] = mapped_column(Integer)
    processing_ms: Mapped[float] = mapped_column(Float)

    num_log_lines: Mapped[int | None] = mapped_column(Integer, nullable=True)
    num_events: Mapped[int | None] = mapped_column(Integer, nullable=True)
    num_windows: Mapped[int | None] = mapped_column(Integer, nullable=True)

    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_anomaly: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    error_message: Mapped[str | None] = mapped_column(String, nullable=True)


def save_history_item(
    db: Session,
    *,
    block_id: str | None,
    status_code: int,
    processing_ms: float,
    num_log_lines: int | None = None,
    num_events: int | None = None,
    num_windows: int | None = None,
    score: float | None = None,
    threshold: float | None = None,
    is_anomaly: bool | None = None,
    error_message: str | None = None,
) -> RequestHistory:
    """Persist one API request outcome in the history table."""
    item = RequestHistory(
        block_id=block_id,
        status_code=status_code,
        processing_ms=processing_ms,
        num_log_lines=num_log_lines,
        num_events=num_events,
        num_windows=num_windows,
        score=score,
        threshold=threshold,
        is_anomaly=is_anomaly,
        error_message=error_message,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def list_history(db: Session) -> list[RequestHistory]:
    """Return request history ordered from newest to oldest."""
    return db.query(RequestHistory).order_by(RequestHistory.id.desc()).all()


def clear_history(db: Session) -> int:
    """Delete all request history rows and return the number of deleted rows."""
    deleted = db.query(RequestHistory).delete()
    db.commit()
    return deleted


def request_stats(db: Session) -> dict:
    """Compute aggregate request statistics from stored history rows."""
    rows = db.query(RequestHistory).all()

    total_requests = len(rows)
    successful_requests = sum(row.status_code == 200 for row in rows)
    failed_requests = total_requests - successful_requests

    processing_times = [row.processing_ms for row in rows if row.processing_ms is not None]

    num_log_lines = [row.num_log_lines for row in rows if row.num_log_lines is not None]

    if processing_times:
        processing_array = np.asarray(processing_times, dtype=float)
        mean_processing_ms = float(processing_array.mean())
        p50_processing_ms = float(np.quantile(processing_array, 0.50))
        p95_processing_ms = float(np.quantile(processing_array, 0.95))
        p99_processing_ms = float(np.quantile(processing_array, 0.99))
    else:
        mean_processing_ms = None
        p50_processing_ms = None
        p95_processing_ms = None
        p99_processing_ms = None

    if num_log_lines:
        num_log_lines_array = np.asarray(num_log_lines, dtype=float)
        mean_num_log_lines = float(num_log_lines_array.mean())
        min_num_log_lines = int(num_log_lines_array.min())
        max_num_log_lines = int(num_log_lines_array.max())
    else:
        mean_num_log_lines = None
        min_num_log_lines = None
        max_num_log_lines = None

    return {
        "total_requests": total_requests,
        "successful_requests": successful_requests,
        "failed_requests": failed_requests,
        "mean_processing_ms": mean_processing_ms,
        "p50_processing_ms": p50_processing_ms,
        "p95_processing_ms": p95_processing_ms,
        "p99_processing_ms": p99_processing_ms,
        "mean_num_log_lines": mean_num_log_lines,
        "min_num_log_lines": min_num_log_lines,
        "max_num_log_lines": max_num_log_lines,
    }
