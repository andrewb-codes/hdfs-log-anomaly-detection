import pytest
from pydantic import ValidationError

from hdfs_anomaly.app.schemas.model import (
    ModelInfoResponse,
    PredictRequest,
    PredictResponse,
)

pytestmark = pytest.mark.no_db


def test_predict_request_strips_block_id_and_log_lines() -> None:
    request = PredictRequest(block_id="  blk_1  ", log_lines=["  line 1  "])

    assert request.block_id == "blk_1"
    assert request.log_lines == ["line 1"]
    assert request.return_event_ids is False
    assert request.return_window_scores is False


def test_predict_request_accepts_return_flags() -> None:
    request = PredictRequest(
        block_id="blk_1",
        log_lines=["line 1"],
        return_event_ids=True,
        return_window_scores=True,
    )

    assert request.return_event_ids is True
    assert request.return_window_scores is True


@pytest.mark.parametrize(
    "payload",
    [
        {"block_id": "", "log_lines": ["line 1"]},
        {"block_id": "   ", "log_lines": ["line 1"]},
        {"block_id": "blk_1", "log_lines": []},
        {"block_id": "blk_1", "log_lines": ["   "]},
    ],
)
def test_predict_request_rejects_empty_values(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        PredictRequest.model_validate(payload)


def test_predict_response_accepts_optional_debug_outputs() -> None:
    response = PredictResponse(
        block_id="blk_1",
        score=0.7,
        threshold=0.5,
        is_anomaly=True,
        scoring_strategy="nll_max",
        num_log_lines=2,
        num_events=3,
        num_windows=1,
        event_ids=[1, 2, 3],
        window_scores=[0.7],
    )

    assert response.event_ids == [1, 2, 3]
    assert response.window_scores == [0.7]


def test_predict_response_defaults_optional_debug_outputs_to_none() -> None:
    response = PredictResponse(
        block_id="blk_1",
        score=0.7,
        threshold=0.5,
        is_anomaly=True,
        scoring_strategy="nll_max",
        num_log_lines=2,
        num_events=3,
        num_windows=1,
    )

    assert response.event_ids is None
    assert response.window_scores is None


def test_model_info_response_accepts_resource_metadata() -> None:
    response = ModelInfoResponse(
        model_type="many_to_many_lstm",
        scoring_strategy="nll_max",
        threshold=0.5,
        window_size=8,
        stride=1,
        device="cpu",
    )

    assert response.model_type == "many_to_many_lstm"
    assert response.threshold == 0.5
    assert response.device == "cpu"
