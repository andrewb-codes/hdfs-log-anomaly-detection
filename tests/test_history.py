from httpx import AsyncClient
from sqlalchemy import text

from hdfs_anomaly.app.db.session import AsyncSessionLocal
from tests.helpers import make_admin, register_and_login

HISTORY_ITEM_FIELDS = {
    "id",
    "created_at",
    "block_id",
    "status_code",
    "processing_ms",
    "num_log_lines",
    "num_events",
    "num_windows",
    "score",
    "threshold",
    "is_anomaly",
    "error_message",
}

STATS_FIELDS = {
    "total_requests",
    "successful_requests",
    "failed_requests",
    "mean_processing_ms",
    "p50_processing_ms",
    "p95_processing_ms",
    "p99_processing_ms",
    "mean_num_log_lines",
    "min_num_log_lines",
    "max_num_log_lines",
}


async def create_history_item(
    *,
    profile_id: int,
    block_id: str,
    status_code: int = 200,
    processing_ms: float = 10.0,
    num_log_lines: int = 2,
    num_events: int = 3,
    num_windows: int = 1,
    score: float | None = 0.7,
    threshold: float | None = 0.5,
    is_anomaly: bool | None = True,
    error_message: str | None = None,
) -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(
            text(
                """
                INSERT INTO request_history (
                    profile_id,
                    block_id,
                    status_code,
                    processing_ms,
                    num_log_lines,
                    num_events,
                    num_windows,
                    score,
                    threshold,
                    is_anomaly,
                    error_message
                )
                VALUES (
                    :profile_id,
                    :block_id,
                    :status_code,
                    :processing_ms,
                    :num_log_lines,
                    :num_events,
                    :num_windows,
                    :score,
                    :threshold,
                    :is_anomaly,
                    :error_message
                )
                """
            ),
            {
                "profile_id": profile_id,
                "block_id": block_id,
                "status_code": status_code,
                "processing_ms": processing_ms,
                "num_log_lines": num_log_lines,
                "num_events": num_events,
                "num_windows": num_windows,
                "score": score,
                "threshold": threshold,
                "is_anomaly": is_anomaly,
                "error_message": error_message,
            },
        )
        await session.commit()


async def test_list_profile_history(client: AsyncClient) -> None:
    token = await register_and_login(client)
    await create_history_item(profile_id=1, block_id="blk_1")

    response = await client.get(
        "/api/v1/history",
        headers={"Authorization": f"Bearer {token}"},
    )

    body = response.json()

    assert response.status_code == 200
    assert set(body) == {"items", "has_next"}
    assert body["has_next"] is False
    assert len(body["items"]) == 1
    assert set(body["items"][0]) == HISTORY_ITEM_FIELDS
    assert body["items"][0]["block_id"] == "blk_1"


async def test_list_profile_history_pagination_has_next(client: AsyncClient) -> None:
    token = await register_and_login(client)
    await create_history_item(profile_id=1, block_id="blk_1")
    await create_history_item(profile_id=1, block_id="blk_2")

    first_page_response = await client.get(
        "/api/v1/history?page=1&page_size=1",
        headers={"Authorization": f"Bearer {token}"},
    )
    second_page_response = await client.get(
        "/api/v1/history?page=2&page_size=1",
        headers={"Authorization": f"Bearer {token}"},
    )

    first_page = first_page_response.json()
    second_page = second_page_response.json()

    assert first_page_response.status_code == 200
    assert second_page_response.status_code == 200
    assert len(first_page["items"]) == 1
    assert first_page["has_next"] is True
    assert len(second_page["items"]) == 1
    assert second_page["has_next"] is False


async def test_list_all_history_requires_admin(client: AsyncClient) -> None:
    token = await register_and_login(client)

    response = await client.get(
        "/api/v1/history/all",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "error.auth.forbidden"}


async def test_admin_can_list_all_history(client: AsyncClient) -> None:
    admin_token = await register_and_login(client, email="admin@mail.com")
    await register_and_login(client, email="user@mail.com")
    await make_admin(profile_id=1)
    await create_history_item(profile_id=1, block_id="admin_blk")
    await create_history_item(profile_id=2, block_id="user_blk")

    response = await client.get(
        "/api/v1/history/all",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    body = response.json()

    assert response.status_code == 200
    assert len(body["items"]) == 2
    assert {item["block_id"] for item in body["items"]} == {"admin_blk", "user_blk"}


async def test_profile_history_stats(client: AsyncClient) -> None:
    token = await register_and_login(client)
    await create_history_item(profile_id=1, block_id="ok", status_code=200)
    await create_history_item(
        profile_id=1,
        block_id="failed",
        status_code=422,
        score=None,
        threshold=None,
        is_anomaly=None,
        error_message="model couldn't process data",
    )

    response = await client.get(
        "/api/v1/history/stats",
        headers={"Authorization": f"Bearer {token}"},
    )

    body = response.json()

    assert response.status_code == 200
    assert set(body) == STATS_FIELDS
    assert body["total_requests"] == 2
    assert body["successful_requests"] == 1
    assert body["failed_requests"] == 1
    assert body["mean_processing_ms"] is not None


async def test_all_history_stats_requires_admin(client: AsyncClient) -> None:
    token = await register_and_login(client)

    response = await client.get(
        "/api/v1/history/stats/all",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "error.auth.forbidden"}


async def test_admin_can_get_all_history_stats(client: AsyncClient) -> None:
    admin_token = await register_and_login(client, email="admin@mail.com")
    await register_and_login(client, email="user@mail.com")
    await make_admin(profile_id=1)
    await create_history_item(profile_id=1, block_id="admin_blk")
    await create_history_item(profile_id=2, block_id="user_blk")

    response = await client.get(
        "/api/v1/history/stats/all",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    body = response.json()

    assert response.status_code == 200
    assert set(body) == STATS_FIELDS
    assert body["total_requests"] == 2
    assert body["successful_requests"] == 2
    assert body["failed_requests"] == 0


async def test_clear_profile_history(client: AsyncClient) -> None:
    token = await register_and_login(client)
    await create_history_item(profile_id=1, block_id="blk_1")
    await create_history_item(profile_id=1, block_id="blk_2")

    response = await client.delete(
        "/api/v1/history",
        headers={"Authorization": f"Bearer {token}"},
    )
    list_response = await client.get(
        "/api/v1/history",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == {"deleted": 2}
    assert list_response.json() == {"items": [], "has_next": False}


async def test_clear_all_history_requires_admin(client: AsyncClient) -> None:
    token = await register_and_login(client)

    response = await client.delete(
        "/api/v1/history/all",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "error.auth.forbidden"}


async def test_admin_can_clear_all_history(client: AsyncClient) -> None:
    admin_token = await register_and_login(client, email="admin@mail.com")
    await register_and_login(client, email="user@mail.com")
    await make_admin(profile_id=1)
    await create_history_item(profile_id=1, block_id="admin_blk")
    await create_history_item(profile_id=2, block_id="user_blk")

    response = await client.delete(
        "/api/v1/history/all",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    list_response = await client.get(
        "/api/v1/history/all",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    assert response.json() == {"deleted": 2}
    assert list_response.json() == {"items": [], "has_next": False}
