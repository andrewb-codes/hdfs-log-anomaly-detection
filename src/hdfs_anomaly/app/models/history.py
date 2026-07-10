from datetime import UTC, datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hdfs_anomaly.app.db.base import Base
from hdfs_anomaly.app.models.profile import Profile


def utc_now() -> datetime:
    """Return the current UTC timestamp for history records."""
    return datetime.now(UTC)


class RequestHistory(Base):
    __tablename__ = "request_history"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("profile.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    profile: Mapped["Profile"] = relationship()

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
