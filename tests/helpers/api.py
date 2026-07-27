from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass

from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from hdfs_anomaly.app.api.main import app
from hdfs_anomaly.app.rate_limit.deps import get_rate_limit_service
from hdfs_anomaly.app.rate_limit.rules import RateLimitRule
from hdfs_anomaly.app.rate_limit.service import RateLimitResult

from .db import activate_profile, make_admin


@dataclass(frozen=True)
class TestUser:
    id: int
    email: str
    password: str
    token: str

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}


class FakeRateLimitService:
    enabled = True

    def __init__(self, *, denied_scope: str | None = None) -> None:
        self.denied_scope = denied_scope
        self.calls: list[tuple[RateLimitRule, str]] = []

    async def hit(self, *, rule: RateLimitRule, key: str, cost: int = 1) -> RateLimitResult:
        self.calls.append((rule, key))

        allowed = rule.scope != self.denied_scope

        return RateLimitResult(
            allowed=allowed,
            limit=1,
            remaining=0 if not allowed else 1,
            reset_at=123,
            retry_after=42,
        )


@asynccontextmanager
async def app_client() -> AsyncIterator[AsyncClient]:
    try:
        async with (
            LifespanManager(app),
            AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client,
        ):
            yield client
    finally:
        app.dependency_overrides.clear()


@contextmanager
def override_rate_limit_service(service: FakeRateLimitService) -> Iterator[FakeRateLimitService]:
    app.dependency_overrides[get_rate_limit_service] = lambda: service

    try:
        yield service
    finally:
        app.dependency_overrides.pop(get_rate_limit_service, None)


async def register_user(
    client: AsyncClient, email: str = "user@mail.com", password: str = "123456"
) -> TestUser:
    registration_response = await client.post(
        "/api/v1/registration",
        json={"email": email, "password": password},
    )
    profile_id = int(registration_response.json()["id"])

    await activate_profile(profile_id)

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )

    return TestUser(
        id=profile_id,
        email=email.strip().lower(),
        password=password,
        token=str(login_response.json()["access_token"]),
    )


async def register_admin(
    client: AsyncClient, email: str = "admin@mail.com", password: str = "123456"
) -> TestUser:
    user = await register_user(client, email=email, password=password)
    await make_admin(user.id)
    return user
