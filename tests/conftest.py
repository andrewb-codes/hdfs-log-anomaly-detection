from collections.abc import AsyncGenerator
from types import SimpleNamespace

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

import hdfs_anomaly.app.api.main as api_main
from hdfs_anomaly.app.db.session import AsyncSessionLocal


@pytest.fixture(autouse=True)
async def clean_db() -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("TRUNCATE TABLE profile, request_history RESTART IDENTITY CASCADE")
        )
        await session.commit()


@pytest.fixture
async def client(monkeypatch: pytest.MonkeyPatch) -> AsyncGenerator[AsyncClient, None]:
    fake_resources = SimpleNamespace(
        scoring_strategy="nll_max",
        threshold=0.5,
        window_size=8,
        stride=1,
        device="cpu",
    )
    monkeypatch.setattr(api_main, "load_resources", lambda: fake_resources)

    async with (
        LifespanManager(api_main.app),
        AsyncClient(
            transport=ASGITransport(app=api_main.app),
            base_url="http://test",
        ) as client,
    ):
        yield client
