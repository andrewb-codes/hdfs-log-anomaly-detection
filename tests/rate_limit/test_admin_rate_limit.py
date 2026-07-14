from httpx import AsyncClient

from hdfs_anomaly.app.api.main import app
from hdfs_anomaly.app.rate_limit.deps import get_rate_limit_service
from hdfs_anomaly.app.rate_limit.rules import ADMIN_READ_LIMIT, ADMIN_WRITE_LIMIT
from tests.helpers import FakeRateLimitService, make_admin, register_and_login


async def test_admin_search_profiles_applies_admin_read_rate_limit(client: AsyncClient) -> None:
    token = await register_and_login(client, email="admin@mail.com")
    await make_admin(1)

    service = FakeRateLimitService()
    app.dependency_overrides[get_rate_limit_service] = lambda: service

    try:
        response = await client.get(
            "/api/v1/admin/profiles",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app.dependency_overrides.pop(get_rate_limit_service, None)

    assert response.status_code == 200

    rule, key = service.calls[0]

    assert rule.scope == ADMIN_READ_LIMIT.scope
    assert key == "rate-limit:admin_read:user:1"


async def test_admin_search_profiles_returns_429_when_rate_limit_exceeded(
    client: AsyncClient,
) -> None:
    token = await register_and_login(client, email="admin@mail.com")
    await make_admin(1)

    service = FakeRateLimitService(denied_scope=ADMIN_READ_LIMIT.scope)
    app.dependency_overrides[get_rate_limit_service] = lambda: service

    try:
        response = await client.get(
            "/api/v1/admin/profiles",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app.dependency_overrides.pop(get_rate_limit_service, None)

    assert response.status_code == 429
    assert response.json() == {"detail": "error.rate_limit.exceeded"}
    assert response.headers["Retry-After"] == "42"


async def test_admin_change_status_applies_admin_write_rate_limit(client: AsyncClient) -> None:
    admin_token = await register_and_login(client, email="admin@mail.com")
    await make_admin(1)
    await register_and_login(client, email="user@mail.com")

    service = FakeRateLimitService()
    app.dependency_overrides[get_rate_limit_service] = lambda: service

    try:
        response = await client.patch(
            "/api/v1/admin/profiles/2/status",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"status": "ACTIVE", "version": 0},
        )
    finally:
        app.dependency_overrides.pop(get_rate_limit_service, None)

    assert response.status_code == 200

    rule, key = service.calls[0]

    assert rule.scope == ADMIN_WRITE_LIMIT.scope
    assert key == "rate-limit:admin_write:user:1"


async def test_admin_change_status_returns_429_when_rate_limit_exceeded(
    client: AsyncClient,
) -> None:
    admin_token = await register_and_login(client, email="admin@mail.com")
    await make_admin(1)
    await register_and_login(client, email="user@mail.com")

    service = FakeRateLimitService(denied_scope=ADMIN_WRITE_LIMIT.scope)
    app.dependency_overrides[get_rate_limit_service] = lambda: service

    try:
        response = await client.patch(
            "/api/v1/admin/profiles/2/status",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"status": "ACTIVE", "version": 0},
        )
    finally:
        app.dependency_overrides.pop(get_rate_limit_service, None)

    assert response.status_code == 429
    assert response.json() == {"detail": "error.rate_limit.exceeded"}
    assert response.headers["Retry-After"] == "42"


async def test_admin_change_role_applies_admin_write_rate_limit(client: AsyncClient) -> None:
    admin_token = await register_and_login(client, email="admin@mail.com")
    await make_admin(1)
    await register_and_login(client, email="user@mail.com")

    service = FakeRateLimitService()
    app.dependency_overrides[get_rate_limit_service] = lambda: service

    try:
        response = await client.patch(
            "/api/v1/admin/profiles/2/role",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"role": "ADMIN", "version": 0},
        )
    finally:
        app.dependency_overrides.pop(get_rate_limit_service, None)

    assert response.status_code == 200

    rule, key = service.calls[0]

    assert rule.scope == ADMIN_WRITE_LIMIT.scope
    assert key == "rate-limit:admin_write:user:1"


async def test_admin_change_role_returns_429_when_rate_limit_exceeded(
    client: AsyncClient,
) -> None:
    admin_token = await register_and_login(client, email="admin@mail.com")
    await make_admin(1)
    await register_and_login(client, email="user@mail.com")

    service = FakeRateLimitService(denied_scope=ADMIN_WRITE_LIMIT.scope)
    app.dependency_overrides[get_rate_limit_service] = lambda: service

    try:
        response = await client.patch(
            "/api/v1/admin/profiles/2/role",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"role": "ADMIN", "version": 0},
        )
    finally:
        app.dependency_overrides.pop(get_rate_limit_service, None)

    assert response.status_code == 429
    assert response.json() == {"detail": "error.rate_limit.exceeded"}
    assert response.headers["Retry-After"] == "42"
