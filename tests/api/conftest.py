from collections.abc import AsyncGenerator
from types import SimpleNamespace

import pytest
from httpx import AsyncClient

import hdfs_anomaly.app.api.main as api_main
from tests.helpers import app_client


@pytest.fixture
async def client(
    monkeypatch: pytest.MonkeyPatch,
    fake_resources: SimpleNamespace,
) -> AsyncGenerator[AsyncClient, None]:
    monkeypatch.setattr(api_main, "load_resources", lambda: fake_resources)

    async with app_client() as client:
        yield client
