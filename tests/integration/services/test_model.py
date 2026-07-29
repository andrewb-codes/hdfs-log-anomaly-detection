from typing import Any, cast

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from hdfs_anomaly.app.model.resources import InferenceResources
from hdfs_anomaly.app.schemas.model import PredictRequest, PredictResponse
from hdfs_anomaly.app.services.history import HistoryService
from hdfs_anomaly.app.services.model import ModelService
from tests.helpers import add_profile


def make_test_resources() -> InferenceResources:
    # run_inference is monkeypatched in these tests, so model and transformer are never used.
    return InferenceResources(
        model=cast(Any, object()),
        transformer=object(),
        threshold=0.5,
        scoring_strategy="nll_max",
        window_size=8,
        stride=1,
        device="cpu",
    )


async def test_model_service_predict_returns_response_and_saves_success_history(
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = await add_profile(session, email="user@mail.com")
    await session.commit()
    resources = make_test_resources()

    def fake_run_inference(request: PredictRequest, resources: Any) -> PredictResponse:
        return PredictResponse(
            block_id=request.block_id,
            score=0.7,
            threshold=resources.threshold,
            is_anomaly=True,
            scoring_strategy=resources.scoring_strategy,
            num_log_lines=len(request.log_lines),
            num_events=3,
            num_windows=1,
        )

    monkeypatch.setattr("hdfs_anomaly.app.services.model.run_inference", fake_run_inference)
    history_service = HistoryService(session)
    service = ModelService(history_service=history_service, resources=resources)

    response = await service.predict(
        request=PredictRequest(block_id="blk_1", log_lines=["line 1", "line 2"]),
        profile_id=profile.id,
    )
    history_items, has_next = await history_service.list_profile_history(
        page=1,
        page_size=10,
        profile_id=profile.id,
    )

    assert response.block_id == "blk_1"
    assert response.score == 0.7
    assert response.is_anomaly is True
    assert has_next is False
    assert len(history_items) == 1
    assert history_items[0].status_code == 200
    assert history_items[0].num_log_lines == 2
    assert history_items[0].num_events == 3
    assert history_items[0].num_windows == 1
    assert history_items[0].score == 0.7
    assert history_items[0].threshold == 0.5
    assert history_items[0].is_anomaly is True


async def test_model_service_predict_saves_failed_history_on_inference_error(
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = await add_profile(session, email="user@mail.com")
    await session.commit()
    resources = make_test_resources()

    def fake_run_inference(_request: PredictRequest, _resources: Any) -> PredictResponse:
        raise RuntimeError("boom")

    monkeypatch.setattr("hdfs_anomaly.app.services.model.run_inference", fake_run_inference)
    history_service = HistoryService(session)
    service = ModelService(history_service=history_service, resources=resources)

    with pytest.raises(HTTPException) as exc_info:
        await service.predict(
            request=PredictRequest(block_id="blk_1", log_lines=["line 1"]),
            profile_id=profile.id,
        )

    history_items, has_next = await history_service.list_profile_history(
        page=1,
        page_size=10,
        profile_id=profile.id,
    )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "model couldn`t process data"
    assert has_next is False
    assert len(history_items) == 1
    assert history_items[0].block_id == "blk_1"
    assert history_items[0].status_code == 422
    assert history_items[0].num_log_lines == 1
    assert history_items[0].num_events is None
    assert history_items[0].num_windows is None
    assert history_items[0].error_message == "model couldn't process data"
