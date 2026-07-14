from collections.abc import AsyncGenerator
from types import SimpleNamespace

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

import hdfs_anomaly.app.api.main as api_main
from hdfs_anomaly.app.db.session import AsyncSessionLocal
from hdfs_anomaly.app.rate_limit.rules import RateLimitRule
from hdfs_anomaly.app.rate_limit.service import RateLimitResult


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


@pytest.fixture(autouse=True)
async def clean_db() -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("TRUNCATE TABLE profile, request_history RESTART IDENTITY CASCADE")
        )
        await session.commit()


@pytest.fixture
def fake_resources() -> SimpleNamespace:
    return SimpleNamespace(
        scoring_strategy="nll_max",
        threshold=0.5,
        window_size=8,
        stride=1,
        device="cpu",
    )


@pytest.fixture
async def client(
    monkeypatch: pytest.MonkeyPatch, fake_resources: SimpleNamespace
) -> AsyncGenerator[AsyncClient, None]:
    monkeypatch.setattr(api_main, "load_resources", lambda: fake_resources)

    async with (
        LifespanManager(api_main.app),
        AsyncClient(
            transport=ASGITransport(app=api_main.app),
            base_url="http://test",
        ) as client,
    ):
        yield client
