from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from hdfs_anomaly.app.models.history import RequestHistory
from hdfs_anomaly.app.repositories.history import HistoryRepository


class HistoryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = HistoryRepository(session)

    async def save_history_item(
        self,
        *,
        profile_id: int,
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
        item = await self.repository.save_request(
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
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def list_profile_history(
        self,
        *,
        page: int,
        page_size: int,
        profile_id: int,
    ) -> tuple[list[RequestHistory], bool]:
        normalized_page = max(page, 1)
        normalized_page_size = max(page_size, 1)

        limit = normalized_page_size + 1
        offset = (normalized_page - 1) * normalized_page_size

        items = await self.repository.list_profile_history(
            profile_id=profile_id,
            limit=limit,
            offset=offset,
        )

        has_next = len(items) > normalized_page_size

        if has_next:
            items = items[:normalized_page_size]

        return items, has_next

    async def list_all_history(
        self,
        *,
        page: int,
        page_size: int,
    ) -> tuple[list[RequestHistory], bool]:
        normalized_page = max(page, 1)
        normalized_page_size = max(page_size, 1)

        limit = normalized_page_size + 1
        offset = (normalized_page - 1) * normalized_page_size

        items = await self.repository.list_all_history(
            limit=limit,
            offset=offset,
        )

        has_next = len(items) > normalized_page_size

        if has_next:
            items = items[:normalized_page_size]

        return items, has_next

    async def request_profile_stats(self, *, profile_id: int) -> Sequence[RequestHistory]:
        return await self.repository.request_profile_stats(profile_id=profile_id)

    async def request_all_stats(self) -> Sequence[RequestHistory]:
        return await self.repository.request_all_stats()

    async def clear_profile_history(self, *, profile_id: int) -> int:
        deleted_count = await self.repository.clear_profile_history(profile_id=profile_id)
        await self.session.commit()
        return deleted_count

    async def clear_all_history(self) -> int:
        deleted_count = await self.repository.clear_all_history()
        await self.session.commit()
        return deleted_count
