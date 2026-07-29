from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from hdfs_anomaly.app.models.history import RequestHistory
from hdfs_anomaly.app.repositories.history import HistoryRepository
from hdfs_anomaly.app.services.history import HistoryService

pytestmark = pytest.mark.no_db


def make_history_service(
    repository: SimpleNamespace,
    session: SimpleNamespace | None = None,
) -> HistoryService:
    session = session or SimpleNamespace(commit=AsyncMock(), refresh=AsyncMock())
    service = HistoryService(cast(AsyncSession, cast(object, session)))
    service.repository = cast(HistoryRepository, cast(object, repository))
    return service


async def test_save_history_item_persists_refreshes_and_returns_item() -> None:
    item = RequestHistory(
        id=10,
        profile_id=1,
        block_id="blk_1",
        status_code=200,
        processing_ms=12.5,
    )
    repository = SimpleNamespace(save_request=AsyncMock(return_value=item))
    session = SimpleNamespace(commit=AsyncMock(), refresh=AsyncMock())
    service = make_history_service(repository=repository, session=session)

    result = await service.save_history_item(
        profile_id=1,
        block_id="blk_1",
        status_code=200,
        processing_ms=12.5,
        num_log_lines=2,
        num_events=3,
        num_windows=1,
        score=0.7,
        threshold=0.5,
        is_anomaly=True,
        error_message=None,
    )

    repository.save_request.assert_awaited_once_with(
        profile_id=1,
        block_id="blk_1",
        status_code=200,
        processing_ms=12.5,
        num_log_lines=2,
        num_events=3,
        num_windows=1,
        score=0.7,
        threshold=0.5,
        is_anomaly=True,
        error_message=None,
    )
    session.commit.assert_awaited_once_with()
    session.refresh.assert_awaited_once_with(item)
    assert result is item


async def test_list_profile_history_normalizes_pagination_and_trims_extra_item() -> None:
    first = RequestHistory(id=1, profile_id=10, status_code=200, processing_ms=1.0)
    second = RequestHistory(id=2, profile_id=10, status_code=200, processing_ms=2.0)
    repository = SimpleNamespace(list_profile_history=AsyncMock(return_value=[first, second]))
    service = make_history_service(repository=repository)

    items, has_next = await service.list_profile_history(
        page=0,
        page_size=1,
        profile_id=10,
    )

    repository.list_profile_history.assert_awaited_once_with(
        profile_id=10,
        limit=2,
        offset=0,
    )
    assert items == [first]
    assert has_next is True


async def test_list_all_history_uses_page_offset_and_reports_no_next_page() -> None:
    item = RequestHistory(id=3, profile_id=10, status_code=422, processing_ms=3.0)
    repository = SimpleNamespace(list_all_history=AsyncMock(return_value=[item]))
    service = make_history_service(repository=repository)

    items, has_next = await service.list_all_history(page=3, page_size=2)

    repository.list_all_history.assert_awaited_once_with(limit=3, offset=4)
    assert items == [item]
    assert has_next is False


async def test_stats_methods_delegate_to_repository() -> None:
    stats = [RequestHistory(id=1, profile_id=10, status_code=200, processing_ms=1.0)]
    repository = SimpleNamespace(
        request_profile_stats=AsyncMock(return_value=stats),
        request_all_stats=AsyncMock(return_value=stats),
    )
    service = make_history_service(repository=repository)

    assert await service.request_profile_stats(profile_id=10) == stats
    assert await service.request_all_stats() == stats

    repository.request_profile_stats.assert_awaited_once_with(profile_id=10)
    repository.request_all_stats.assert_awaited_once_with()


async def test_clear_history_methods_commit_and_return_deleted_count() -> None:
    repository = SimpleNamespace(
        clear_profile_history=AsyncMock(return_value=2),
        clear_all_history=AsyncMock(return_value=5),
    )
    session = SimpleNamespace(commit=AsyncMock(), refresh=AsyncMock())
    service = make_history_service(repository=repository, session=session)

    profile_deleted = await service.clear_profile_history(profile_id=10)
    all_deleted = await service.clear_all_history()

    repository.clear_profile_history.assert_awaited_once_with(profile_id=10)
    repository.clear_all_history.assert_awaited_once_with()
    assert session.commit.await_count == 2
    assert profile_deleted == 2
    assert all_deleted == 5
