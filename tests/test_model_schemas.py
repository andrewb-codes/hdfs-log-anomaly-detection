import pytest
from pydantic import ValidationError

from hdfs_anomaly.app.schemas.model import PredictRequest

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
