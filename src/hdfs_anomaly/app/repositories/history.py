from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from hdfs_anomaly.app.models.history import RequestHistory


class HistoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save_request(
        self,
        *,
        profile_id: int,
        block_id: str | None,
        status_code: int,
        processing_ms: float,
        num_log_lines: int | None,
        num_events: int | None,
        num_windows: int | None,
        score: float | None,
        threshold: float | None,
        is_anomaly: bool | None,
        error_message: str | None,
    ) -> RequestHistory:
        item = RequestHistory(
            profile_id=profile_id,
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
        self.session.add(item)
        await self.session.flush()
        return item

    async def list_profile_history(
        self, *, profile_id: int, limit: int, offset: int
    ) -> list[RequestHistory]:
        query = (
            select(RequestHistory)
            .where(RequestHistory.profile_id == profile_id)
            .order_by(RequestHistory.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.scalars(query)
        return list(result)

    async def list_all_history(self, *, limit: int, offset: int) -> list[RequestHistory]:
        query = (
            select(RequestHistory)
            .order_by(RequestHistory.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.scalars(query)
        return list(result)

    async def request_profile_stats(self, *, profile_id: int) -> Sequence[RequestHistory]:
        query = select(RequestHistory).where(RequestHistory.profile_id == profile_id)
        result = await self.session.scalars(query)
        return result.all()

    async def request_all_stats(self) -> Sequence[RequestHistory]:
        query = select(RequestHistory)
        result = await self.session.scalars(query)
        return result.all()

    async def clear_profile_history(self, *, profile_id: int) -> int:
        query = (
            delete(RequestHistory)
            .where(RequestHistory.profile_id == profile_id)
            .returning(RequestHistory.id)
        )
        result = await self.session.scalars(query)
        return len(result.all())

    async def clear_all_history(self) -> int:
        query = delete(RequestHistory).returning(RequestHistory.id)
        result = await self.session.scalars(query)
        return len(result.all())
