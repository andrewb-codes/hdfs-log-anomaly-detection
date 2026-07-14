from httpx import AsyncClient

from hdfs_anomaly.app.api.main import app
from hdfs_anomaly.app.rate_limit.deps import get_rate_limit_service
from hdfs_anomaly.app.rate_limit.rules import PROFILE_READ_LIMIT, PROFILE_WRITE_LIMIT
from tests.helpers import FakeRateLimitService, register_and_login


async def test_get_profile_applies_user_rate_limit(client: AsyncClient) -> None:
    token = await register_and_login(client)

    service = FakeRateLimitService()
    app.dependency_overrides[get_rate_limit_service] = lambda: service

    try:
        response = await client.get(
            "/api/v1/profile",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app.dependency_overrides.pop(get_rate_limit_service, None)

    assert response.status_code == 200

    assert len(service.calls) == 1

    rule, key = service.calls[0]

    assert rule.scope == PROFILE_READ_LIMIT.scope
    assert key == "rate-limit:profile_read:user:1"


async def test_get_profile_returns_429_when_rate_limit_exceeded(client: AsyncClient) -> None:
    token = await register_and_login(client)

    service = FakeRateLimitService(denied_scope=PROFILE_READ_LIMIT.scope)
    app.dependency_overrides[get_rate_limit_service] = lambda: service

    try:
        response = await client.get(
            "/api/v1/profile",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app.dependency_overrides.pop(get_rate_limit_service, None)

    assert response.status_code == 429
    assert response.json() == {"detail": "error.rate_limit.exceeded"}
    assert response.headers["Retry-After"] == "42"


async def test_change_email_applies_user_write_rate_limit(client: AsyncClient) -> None:
    token = await register_and_login(client)

    service = FakeRateLimitService()
    app.dependency_overrides[get_rate_limit_service] = lambda: service

    try:
        response = await client.patch(
            "/api/v1/profile/email",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "new_email": "new-user@mail.com",
                "current_password": "123456",
                "version": 0,
            },
        )
    finally:
        app.dependency_overrides.pop(get_rate_limit_service, None)

    assert response.status_code == 200

    rule, key = service.calls[0]

    assert rule.scope == PROFILE_WRITE_LIMIT.scope
    assert key == "rate-limit:profile_write:user:1"


async def test_change_password_applies_user_write_rate_limit(client: AsyncClient) -> None:
    token = await register_and_login(client)

    service = FakeRateLimitService()
    app.dependency_overrides[get_rate_limit_service] = lambda: service

    try:
        response = await client.patch(
            "/api/v1/profile/password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": "123456",
                "new_password": "654321",
                "version": 0,
            },
        )
    finally:
        app.dependency_overrides.pop(get_rate_limit_service, None)

    assert response.status_code == 200

    rule, key = service.calls[0]

    assert rule.scope == PROFILE_WRITE_LIMIT.scope
    assert key == "rate-limit:profile_write:user:1"


async def test_delete_profile_applies_profile_write_rate_limit(client: AsyncClient) -> None:
    token = await register_and_login(client)

    service = FakeRateLimitService()
    app.dependency_overrides[get_rate_limit_service] = lambda: service

    try:
        response = await client.delete(
            "/api/v1/profile",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app.dependency_overrides.pop(get_rate_limit_service, None)

    assert response.status_code == 204

    rule, key = service.calls[0]

    assert rule.scope == PROFILE_WRITE_LIMIT.scope
    assert key == "rate-limit:profile_write:user:1"


async def test_delete_profile_returns_429_when_rate_limit_exceeded(
    client: AsyncClient,
) -> None:
    token = await register_and_login(client)

    service = FakeRateLimitService(denied_scope=PROFILE_WRITE_LIMIT.scope)
    app.dependency_overrides[get_rate_limit_service] = lambda: service

    try:
        response = await client.delete(
            "/api/v1/profile",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app.dependency_overrides.pop(get_rate_limit_service, None)

    assert response.status_code == 429
    assert response.json() == {"detail": "error.rate_limit.exceeded"}
    assert response.headers["Retry-After"] == "42"
