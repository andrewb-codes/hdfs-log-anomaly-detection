from httpx import AsyncClient

from hdfs_anomaly.app.schemas.model import PredictResponse
from tests.helpers import make_admin, register_and_login


async def test_model_info_without_token_returns_401(client: AsyncClient) -> None:
    response = await client.get("/api/v1/model/info")

    assert response.status_code == 401
    assert response.json() == {"detail": "error.auth.unauthorized"}


async def test_user_cannot_get_model_info(client: AsyncClient) -> None:
    token = await register_and_login(client)

    response = await client.get(
        "/api/v1/model/info",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "error.auth.forbidden"}


async def test_admin_can_get_model_info(client: AsyncClient) -> None:
    admin_token = await register_and_login(client, email="admin@mail.com")
    await make_admin(profile_id=1)

    response = await client.get(
        "/api/v1/model/info",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "model_type": "many_to_many_lstm",
        "scoring_strategy": "nll_max",
        "threshold": 0.5,
        "window_size": 8,
        "stride": 1,
        "device": "cpu",
    }


async def test_predict_returns_response_and_writes_history(
    client: AsyncClient,
    monkeypatch,
) -> None:
    token = await register_and_login(client)

    def fake_run_inference(request, resources) -> PredictResponse:
        return PredictResponse(
            block_id=request.block_id,
            score=0.7,
            threshold=resources.threshold,
            is_anomaly=True,
            scoring_strategy=resources.scoring_strategy,
            num_log_lines=len(request.log_lines),
            num_events=3,
            num_windows=1,
            event_ids=[1, 2, 3],
            window_scores=[0.7],
        )

    monkeypatch.setattr("hdfs_anomaly.app.services.model.run_inference", fake_run_inference)

    response = await client.post(
        "/api/v1/model/predict",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "block_id": "blk_1",
            "log_lines": ["line 1", "line 2"],
            "return_event_ids": True,
            "return_window_scores": True,
        },
    )
    history_response = await client.get(
        "/api/v1/history",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "block_id": "blk_1",
        "score": 0.7,
        "threshold": 0.5,
        "is_anomaly": True,
        "scoring_strategy": "nll_max",
        "num_log_lines": 2,
        "num_events": 3,
        "num_windows": 1,
        "event_ids": [1, 2, 3],
        "window_scores": [0.7],
    }

    history_body = history_response.json()
    assert history_response.status_code == 200
    assert len(history_body["items"]) == 1
    assert history_body["items"][0]["block_id"] == "blk_1"
    assert history_body["items"][0]["status_code"] == 200
    assert history_body["items"][0]["is_anomaly"] is True


async def test_predict_invalid_payload_returns_422(client: AsyncClient) -> None:
    token = await register_and_login(client)

    response = await client.post(
        "/api/v1/model/predict",
        headers={"Authorization": f"Bearer {token}"},
        json={"block_id": "", "log_lines": []},
    )

    assert response.status_code == 422


async def test_predict_inference_failure_returns_422_and_writes_failed_history(
    client: AsyncClient,
    monkeypatch,
) -> None:
    token = await register_and_login(client)

    def fake_run_inference(_request, _resources) -> PredictResponse:
        raise RuntimeError("boom")

    monkeypatch.setattr("hdfs_anomaly.app.services.model.run_inference", fake_run_inference)

    response = await client.post(
        "/api/v1/model/predict",
        headers={"Authorization": f"Bearer {token}"},
        json={"block_id": "blk_1", "log_lines": ["line 1"]},
    )
    history_response = await client.get(
        "/api/v1/history",
        headers={"Authorization": f"Bearer {token}"},
    )

    history_body = history_response.json()

    assert response.status_code == 422
    assert response.json() == {"detail": "model couldn`t process data"}
    assert history_response.status_code == 200
    assert len(history_body["items"]) == 1
    assert history_body["items"][0]["status_code"] == 422
    assert history_body["items"][0]["error_message"] == "model couldn't process data"
