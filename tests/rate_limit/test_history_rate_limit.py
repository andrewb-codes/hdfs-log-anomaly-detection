from httpx import AsyncClient

from hdfs_anomaly.app.api.main import app
from hdfs_anomaly.app.rate_limit.deps import get_rate_limit_service
from hdfs_anomaly.app.rate_limit.rules import HISTORY_READ_LIMIT, HISTORY_WRITE_LIMIT
from tests.helpers import FakeRateLimitService, make_admin, register_and_login


async def test_list_history_applies_history_read_rate_limit(
    client: AsyncClient,
) -> None:
    token = await register_and_login(client)

    service = FakeRateLimitService()
    app.dependency_overrides[get_rate_limit_service] = lambda: service

    try:
        response = await client.get(
            "/api/v1/history",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app.dependency_overrides.pop(get_rate_limit_service, None)

    assert response.status_code == 200

    rule, key = service.calls[0]

    assert rule.scope == HISTORY_READ_LIMIT.scope
    assert key == "rate-limit:history_read:user:1"


async def test_history_stats_returns_429_when_read_rate_limit_exceeded(
    client: AsyncClient,
) -> None:
    token = await register_and_login(client)

    service = FakeRateLimitService(denied_scope=HISTORY_READ_LIMIT.scope)
    app.dependency_overrides[get_rate_limit_service] = lambda: service

    try:
        response = await client.get(
            "/api/v1/history/stats",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app.dependency_overrides.pop(get_rate_limit_service, None)

    assert response.status_code == 429
    assert response.json() == {"detail": "error.rate_limit.exceeded"}
    assert response.headers["Retry-After"] == "42"


async def test_clear_history_applies_history_write_rate_limit(
    client: AsyncClient,
) -> None:
    token = await register_and_login(client)

    service = FakeRateLimitService()
    app.dependency_overrides[get_rate_limit_service] = lambda: service

    try:
        response = await client.delete(
            "/api/v1/history",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app.dependency_overrides.pop(get_rate_limit_service, None)

    assert response.status_code == 200

    rule, key = service.calls[0]

    assert rule.scope == HISTORY_WRITE_LIMIT.scope
    assert key == "rate-limit:history_write:user:1"


async def test_admin_list_all_history_applies_history_read_rate_limit(
    client: AsyncClient,
) -> None:
    token = await register_and_login(client, email="admin@mail.com")
    await make_admin(1)

    service = FakeRateLimitService()
    app.dependency_overrides[get_rate_limit_service] = lambda: service

    try:
        response = await client.get(
            "/api/v1/history/all",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app.dependency_overrides.pop(get_rate_limit_service, None)

    assert response.status_code == 200

    rule, key = service.calls[0]

    assert rule.scope == HISTORY_READ_LIMIT.scope
    assert key == "rate-limit:history_read:user:1"


async def test_admin_clear_all_history_returns_429_when_write_rate_limit_exceeded(
    client: AsyncClient,
) -> None:
    token = await register_and_login(client, email="admin@mail.com")
    await make_admin(1)

    service = FakeRateLimitService(denied_scope=HISTORY_WRITE_LIMIT.scope)
    app.dependency_overrides[get_rate_limit_service] = lambda: service

    try:
        response = await client.delete(
            "/api/v1/history/all",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app.dependency_overrides.pop(get_rate_limit_service, None)

    assert response.status_code == 429
    assert response.json() == {"detail": "error.rate_limit.exceeded"}
    assert response.headers["Retry-After"] == "42"
