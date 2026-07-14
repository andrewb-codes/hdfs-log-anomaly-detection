from typing import Any

import pytest
from httpx import AsyncClient

from hdfs_anomaly.app.api.main import app
from hdfs_anomaly.app.rate_limit.deps import get_rate_limit_service
from hdfs_anomaly.app.rate_limit.rules import MODEL_INFO_LIMIT, MODEL_PREDICT_LIMIT
from hdfs_anomaly.app.schemas.model import PredictRequest, PredictResponse
from tests.helpers import FakeRateLimitService, make_admin, register_and_login


@pytest.fixture
def stub_successful_inference(monkeypatch: pytest.MonkeyPatch) -> None:
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
            event_ids=None,
            window_scores=None,
        )

    monkeypatch.setattr("hdfs_anomaly.app.services.model.run_inference", fake_run_inference)


async def test_model_info_applies_model_info_rate_limit(client: AsyncClient) -> None:
    token = await register_and_login(client, email="admin@mail.com")
    await make_admin(1)

    service = FakeRateLimitService()
    app.dependency_overrides[get_rate_limit_service] = lambda: service

    try:
        response = await client.get(
            "/api/v1/model/info",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app.dependency_overrides.pop(get_rate_limit_service, None)

    assert response.status_code == 200

    rule, key = service.calls[0]

    assert rule.scope == MODEL_INFO_LIMIT.scope
    assert key == "rate-limit:model_info:user:1"


async def test_model_info_returns_429_when_rate_limit_exceeded(
    client: AsyncClient,
) -> None:
    token = await register_and_login(client, email="admin@mail.com")
    await make_admin(1)

    service = FakeRateLimitService(denied_scope=MODEL_INFO_LIMIT.scope)
    app.dependency_overrides[get_rate_limit_service] = lambda: service

    try:
        response = await client.get(
            "/api/v1/model/info",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app.dependency_overrides.pop(get_rate_limit_service, None)

    assert response.status_code == 429
    assert response.json() == {"detail": "error.rate_limit.exceeded"}
    assert response.headers["Retry-After"] == "42"


async def test_predict_applies_model_predict_rate_limit(
    client: AsyncClient,
    stub_successful_inference: None,
) -> None:
    token = await register_and_login(client)

    service = FakeRateLimitService()
    app.dependency_overrides[get_rate_limit_service] = lambda: service

    try:
        response = await client.post(
            "/api/v1/model/predict",
            headers={"Authorization": f"Bearer {token}"},
            json={"block_id": "blk_1", "log_lines": ["line 1"]},
        )
    finally:
        app.dependency_overrides.pop(get_rate_limit_service, None)

    assert response.status_code == 200

    rule, key = service.calls[0]

    assert rule.scope == MODEL_PREDICT_LIMIT.scope
    assert key == "rate-limit:model_predict:user:1"


async def test_predict_returns_429_when_rate_limit_exceeded(
    client: AsyncClient,
) -> None:
    token = await register_and_login(client)

    service = FakeRateLimitService(denied_scope=MODEL_PREDICT_LIMIT.scope)
    app.dependency_overrides[get_rate_limit_service] = lambda: service

    try:
        response = await client.post(
            "/api/v1/model/predict",
            headers={"Authorization": f"Bearer {token}"},
            json={"block_id": "blk_1", "log_lines": ["line 1"]},
        )
    finally:
        app.dependency_overrides.pop(get_rate_limit_service, None)

    assert response.status_code == 429
    assert response.json() == {"detail": "error.rate_limit.exceeded"}
    assert response.headers["Retry-After"] == "42"
