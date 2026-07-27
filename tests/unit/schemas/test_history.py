import pytest

from hdfs_anomaly.app.schemas.history import (
    DeleteHistoryResponse,
    HistoryItem,
    HistoryListResponse,
    StatsResponse,
)

pytestmark = pytest.mark.no_db


def test_history_item_accepts_successful_request_payload() -> None:
    item = HistoryItem.model_validate(
        {
            "id": 1,
            "created_at": "2026-07-27T12:00:00",
            "block_id": "blk_1",
            "status_code": 200,
            "processing_ms": 10.5,
            "num_log_lines": 2,
            "num_events": 3,
            "num_windows": 1,
            "score": 0.7,
            "threshold": 0.5,
            "is_anomaly": True,
            "error_message": None,
        }
    )

    assert item.id == 1
    assert item.block_id == "blk_1"
    assert item.is_anomaly is True


def test_history_item_accepts_failed_request_payload() -> None:
    item = HistoryItem.model_validate(
        {
            "id": 1,
            "created_at": "2026-07-27T12:00:00",
            "block_id": None,
            "status_code": 422,
            "processing_ms": 10.5,
            "num_log_lines": None,
            "num_events": None,
            "num_windows": None,
            "score": None,
            "threshold": None,
            "is_anomaly": None,
            "error_message": "model couldn't process data",
        }
    )

    assert item.block_id is None
    assert item.score is None
    assert item.error_message == "model couldn't process data"


def test_history_list_response_accepts_items_and_has_next() -> None:
    item = HistoryItem.model_validate(
        {
            "id": 1,
            "created_at": "2026-07-27T12:00:00",
            "block_id": "blk_1",
            "status_code": 200,
            "processing_ms": 10.5,
            "num_log_lines": 2,
            "num_events": 3,
            "num_windows": 1,
            "score": 0.7,
            "threshold": 0.5,
            "is_anomaly": True,
            "error_message": None,
        }
    )

    response = HistoryListResponse(items=[item], has_next=True)

    assert response.items == [item]
    assert response.has_next is True


def test_delete_history_response_accepts_deleted_count() -> None:
    response = DeleteHistoryResponse(deleted=2)

    assert response.deleted == 2


def test_stats_response_accepts_empty_stats() -> None:
    response = StatsResponse(
        total_requests=0,
        successful_requests=0,
        failed_requests=0,
        mean_processing_ms=None,
        p50_processing_ms=None,
        p95_processing_ms=None,
        p99_processing_ms=None,
        mean_num_log_lines=None,
        min_num_log_lines=None,
        max_num_log_lines=None,
    )

    assert response.total_requests == 0
    assert response.mean_processing_ms is None


def test_stats_response_accepts_aggregated_stats() -> None:
    response = StatsResponse(
        total_requests=3,
        successful_requests=2,
        failed_requests=1,
        mean_processing_ms=10.5,
        p50_processing_ms=10.0,
        p95_processing_ms=20.0,
        p99_processing_ms=25.0,
        mean_num_log_lines=2.5,
        min_num_log_lines=1,
        max_num_log_lines=5,
    )

    assert response.successful_requests == 2
    assert response.failed_requests == 1
    assert response.max_num_log_lines == 5
