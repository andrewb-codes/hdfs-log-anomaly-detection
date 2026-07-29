from collections.abc import Callable
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

import hdfs_anomaly.app.services.model as model_service_module
from hdfs_anomaly.app.model.resources import InferenceResources
from hdfs_anomaly.app.schemas.model import PredictRequest, PredictResponse
from hdfs_anomaly.app.services.history import HistoryService
from hdfs_anomaly.app.services.model import ModelService

pytestmark = pytest.mark.no_db


async def run_inline(
    func: Callable[[PredictRequest, InferenceResources], PredictResponse],
    request: PredictRequest,
    resources: InferenceResources,
) -> PredictResponse:
    return func(request, resources)


async def test_predict_returns_inference_response_and_saves_success_history(
    monkeypatch: pytest.MonkeyPatch,
    fake_resources: InferenceResources,
) -> None:
    saved_history = AsyncMock()
    history_service = cast(
        HistoryService,
        cast(object, SimpleNamespace(save_history_item=saved_history)),
    )
    service = ModelService(history_service=history_service, resources=fake_resources)
    request = PredictRequest(block_id="blk_1", log_lines=["line 1", "line 2"])

    def fake_run_inference(
        inference_request: PredictRequest,
        resources: InferenceResources,
    ) -> PredictResponse:
        assert inference_request is request
        assert resources is fake_resources
        return PredictResponse(
            block_id="blk_1",
            score=0.7,
            threshold=resources.threshold,
            is_anomaly=True,
            scoring_strategy=resources.scoring_strategy,
            num_log_lines=2,
            num_events=3,
            num_windows=1,
        )

    monkeypatch.setattr(model_service_module, "run_in_threadpool", run_inline)
    monkeypatch.setattr(model_service_module, "run_inference", fake_run_inference)

    response = await service.predict(request=request, profile_id=5)

    saved_history.assert_awaited_once()
    saved_call = saved_history.await_args
    assert saved_call is not None
    assert saved_call.kwargs["profile_id"] == 5
    assert saved_call.kwargs["block_id"] == "blk_1"
    assert saved_call.kwargs["status_code"] == 200
    assert saved_call.kwargs["num_log_lines"] == 2
    assert saved_call.kwargs["num_events"] == 3
    assert saved_call.kwargs["num_windows"] == 1
    assert saved_call.kwargs["score"] == 0.7
    assert saved_call.kwargs["threshold"] == 0.5
    assert saved_call.kwargs["is_anomaly"] is True
    assert response.score == 0.7
    assert response.is_anomaly is True


async def test_predict_saves_failed_history_and_converts_inference_error(
    monkeypatch: pytest.MonkeyPatch,
    fake_resources: InferenceResources,
) -> None:
    saved_history = AsyncMock()
    history_service = cast(
        HistoryService,
        cast(object, SimpleNamespace(save_history_item=saved_history)),
    )
    service = ModelService(history_service=history_service, resources=fake_resources)
    request = PredictRequest(block_id="blk_1", log_lines=["line 1"])

    def fake_run_inference(_request: PredictRequest, _resources: Any) -> PredictResponse:
        raise RuntimeError("boom")

    monkeypatch.setattr(model_service_module, "run_in_threadpool", run_inline)
    monkeypatch.setattr(model_service_module, "run_inference", fake_run_inference)

    with pytest.raises(HTTPException) as exc_info:
        await service.predict(request=request, profile_id=5)

    saved_history.assert_awaited_once()
    saved_call = saved_history.await_args
    assert saved_call is not None
    assert saved_call.kwargs["profile_id"] == 5
    assert saved_call.kwargs["block_id"] == "blk_1"
    assert saved_call.kwargs["status_code"] == 422
    assert saved_call.kwargs["num_log_lines"] == 1
    assert saved_call.kwargs["error_message"] == "model couldn't process data"
    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "model couldn`t process data"
