from httpx import AsyncClient

from hdfs_anomaly.app.api.main import app
from hdfs_anomaly.app.rate_limit.deps import get_rate_limit_service
from hdfs_anomaly.app.rate_limit.rules import LOGIN_ACCOUNT_LIMIT, LOGIN_GLOBAL_LIMIT
from tests.conftest import FakeRateLimitService
from tests.helpers import activate_profile


async def test_successful_login_applies_only_global_limit(client: AsyncClient) -> None:
    payload = {"email": "user@mail.com", "password": "123456"}

    response = await client.post("/api/v1/registration", json=payload)
    profile_id = int(response.json()["id"])

    await activate_profile(profile_id)

    service = FakeRateLimitService()
    app.dependency_overrides[get_rate_limit_service] = lambda: service

    try:
        response = await client.post("/api/v1/auth/login", json=payload)
    finally:
        app.dependency_overrides.pop(get_rate_limit_service, None)

    assert response.status_code == 200

    scopes = [rule.scope for rule, _ in service.calls]

    assert scopes == [LOGIN_GLOBAL_LIMIT.scope]


async def test_failed_login_applies_global_and_account_limits(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/registration",
        json={"email": "user@mail.com", "password": "123456"},
    )

    service = FakeRateLimitService()
    app.dependency_overrides[get_rate_limit_service] = lambda: service

    try:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "user@mail.com", "password": "wrong-password"},
        )
    finally:
        app.dependency_overrides.pop(get_rate_limit_service, None)

    assert response.status_code == 401

    scopes = [rule.scope for rule, _ in service.calls]

    assert scopes == [
        LOGIN_GLOBAL_LIMIT.scope,
        LOGIN_ACCOUNT_LIMIT.scope,
    ]


async def test_login_account_key_does_not_contain_raw_email(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/registration",
        json={"email": "user@mail.com", "password": "123456"},
    )

    service = FakeRateLimitService()
    app.dependency_overrides[get_rate_limit_service] = lambda: service

    try:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "user@mail.com", "password": "wrong-password"},
        )
    finally:
        app.dependency_overrides.pop(get_rate_limit_service, None)

    assert response.status_code == 401

    _, global_key = service.calls[0]
    _, account_key = service.calls[1]

    assert global_key == "rate-limit:login_global:global"
    assert account_key.startswith("rate-limit:login_account:account:")
    assert "user@mail.com" not in account_key


async def test_login_returns_429_when_global_limit_exceeded(client: AsyncClient) -> None:
    service = FakeRateLimitService(denied_scope=LOGIN_GLOBAL_LIMIT.scope)
    app.dependency_overrides[get_rate_limit_service] = lambda: service

    try:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "user@mail.com", "password": "123456"},
        )
    finally:
        app.dependency_overrides.pop(get_rate_limit_service, None)

    assert response.status_code == 429
    assert response.json() == {"detail": "error.rate_limit.exceeded"}
    assert response.headers["Retry-After"] == "42"


async def test_failed_login_returns_429_when_account_limit_exceeded(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/registration",
        json={"email": "user@mail.com", "password": "123456"},
    )

    service = FakeRateLimitService(denied_scope=LOGIN_ACCOUNT_LIMIT.scope)
    app.dependency_overrides[get_rate_limit_service] = lambda: service

    try:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "user@mail.com", "password": "wrong-password"},
        )
    finally:
        app.dependency_overrides.pop(get_rate_limit_service, None)

    assert response.status_code == 429
    assert response.json() == {"detail": "error.rate_limit.exceeded"}
    assert response.headers["Retry-After"] == "42"
