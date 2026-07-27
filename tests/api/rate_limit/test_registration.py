from httpx import AsyncClient

from hdfs_anomaly.app.api.main import app
from hdfs_anomaly.app.rate_limit.deps import get_rate_limit_service
from hdfs_anomaly.app.rate_limit.rules import REGISTER_GLOBAL_LIMIT, REGISTER_IDENTIFIER_LIMIT
from tests.helpers import FakeRateLimitService


async def test_registration_applies_global_and_identifier_limits(
    client: AsyncClient,
) -> None:
    service = FakeRateLimitService()
    app.dependency_overrides[get_rate_limit_service] = lambda: service

    try:
        response = await client.post(
            "/api/v1/registration",
            json={"email": "User@Mail.COM", "password": "123456"},
        )
    finally:
        app.dependency_overrides.pop(get_rate_limit_service, None)

    assert response.status_code == 201

    scopes = [rule.scope for rule, _ in service.calls]

    assert scopes == [
        REGISTER_GLOBAL_LIMIT.scope,
        REGISTER_IDENTIFIER_LIMIT.scope,
    ]


async def test_registration_passes_hashed_identifier_key_to_rate_limiter(
    client: AsyncClient,
) -> None:
    service = FakeRateLimitService()
    app.dependency_overrides[get_rate_limit_service] = lambda: service

    try:
        response = await client.post(
            "/api/v1/registration",
            json={"email": "user@mail.com", "password": "123456"},
        )
    finally:
        app.dependency_overrides.pop(get_rate_limit_service, None)

    assert response.status_code == 201

    _, global_key = service.calls[0]
    _, identifier_key = service.calls[1]

    assert global_key == "rate-limit:register_global:global"
    assert identifier_key.startswith("rate-limit:register_identifier:identifier:")
    assert "user@mail.com" not in identifier_key


async def test_registration_returns_429_when_global_limit_exceeded(
    client: AsyncClient,
) -> None:
    service = FakeRateLimitService(denied_scope=REGISTER_GLOBAL_LIMIT.scope)
    app.dependency_overrides[get_rate_limit_service] = lambda: service

    try:
        response = await client.post(
            "/api/v1/registration",
            json={"email": "user@mail.com", "password": "123456"},
        )
    finally:
        app.dependency_overrides.pop(get_rate_limit_service, None)

    assert response.status_code == 429
    assert response.json() == {"detail": "error.rate_limit.exceeded"}
    assert response.headers["Retry-After"] == "42"


async def test_registration_returns_429_when_identifier_limit_exceeded(
    client: AsyncClient,
) -> None:
    service = FakeRateLimitService(denied_scope=REGISTER_IDENTIFIER_LIMIT.scope)
    app.dependency_overrides[get_rate_limit_service] = lambda: service

    try:
        response = await client.post(
            "/api/v1/registration",
            json={"email": "user@mail.com", "password": "123456"},
        )
    finally:
        app.dependency_overrides.pop(get_rate_limit_service, None)

    assert response.status_code == 429
    assert response.json() == {"detail": "error.rate_limit.exceeded"}
    assert response.headers["Retry-After"] == "42"
