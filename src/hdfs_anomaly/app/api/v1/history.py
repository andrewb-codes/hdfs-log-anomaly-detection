from typing import Annotated

from fastapi import APIRouter, Depends, Query

from hdfs_anomaly.app.api.deps import get_current_profile, get_history_service, require_admin
from hdfs_anomaly.app.api.presenters.history import calculate_request_stats
from hdfs_anomaly.app.models.profile import Profile
from hdfs_anomaly.app.rate_limit.deps import rate_limit_user
from hdfs_anomaly.app.rate_limit.rules import HISTORY_READ_LIMIT, HISTORY_WRITE_LIMIT
from hdfs_anomaly.app.schemas.history import (
    DeleteHistoryResponse,
    HistoryItem,
    HistoryListResponse,
    StatsResponse,
)
from hdfs_anomaly.app.services.history import HistoryService

router = APIRouter(prefix="/api/v1/history", tags=["History"])


@router.get("", response_model=HistoryListResponse)
async def list_profile_history(
    profile: Annotated[Profile, Depends(get_current_profile)],
    _: Annotated[None, Depends(rate_limit_user(HISTORY_READ_LIMIT))],
    service: Annotated[HistoryService, Depends(get_history_service)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> HistoryListResponse:
    items, has_next = await service.list_profile_history(
        profile_id=profile.id,
        page=page,
        page_size=page_size,
    )

    return HistoryListResponse(
        items=[HistoryItem.model_validate(item) for item in items],
        has_next=has_next,
    )


@router.get("/all", response_model=HistoryListResponse)
async def list_all_history(
    _: Annotated[Profile, Depends(require_admin)],
    __: Annotated[None, Depends(rate_limit_user(HISTORY_READ_LIMIT))],
    service: Annotated[HistoryService, Depends(get_history_service)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> HistoryListResponse:
    items, has_next = await service.list_all_history(
        page=page,
        page_size=page_size,
    )

    return HistoryListResponse(
        items=[HistoryItem.model_validate(item) for item in items],
        has_next=has_next,
    )


@router.get("/stats", response_model=StatsResponse)
async def request_profile_stats(
    profile: Annotated[Profile, Depends(get_current_profile)],
    _: Annotated[None, Depends(rate_limit_user(HISTORY_READ_LIMIT))],
    service: Annotated[HistoryService, Depends(get_history_service)],
) -> StatsResponse:
    rows = await service.request_profile_stats(profile_id=profile.id)
    return calculate_request_stats(rows)


@router.get("/stats/all", response_model=StatsResponse)
async def request_all_stats(
    _: Annotated[Profile, Depends(require_admin)],
    __: Annotated[None, Depends(rate_limit_user(HISTORY_READ_LIMIT))],
    service: Annotated[HistoryService, Depends(get_history_service)],
) -> StatsResponse:
    rows = await service.request_all_stats()
    return calculate_request_stats(rows)


@router.delete("", response_model=DeleteHistoryResponse)
async def clear_profile_history(
    profile: Annotated[Profile, Depends(get_current_profile)],
    _: Annotated[None, Depends(rate_limit_user(HISTORY_WRITE_LIMIT))],
    service: Annotated[HistoryService, Depends(get_history_service)],
) -> DeleteHistoryResponse:
    deleted = await service.clear_profile_history(profile_id=profile.id)
    return DeleteHistoryResponse(deleted=deleted)


@router.delete("/all", response_model=DeleteHistoryResponse)
async def clear_all_history(
    _: Annotated[Profile, Depends(require_admin)],
    __: Annotated[None, Depends(rate_limit_user(HISTORY_WRITE_LIMIT))],
    service: Annotated[HistoryService, Depends(get_history_service)],
) -> DeleteHistoryResponse:
    deleted = await service.clear_all_history()
    return DeleteHistoryResponse(deleted=deleted)
