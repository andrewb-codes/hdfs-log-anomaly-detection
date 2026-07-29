from collections.abc import AsyncGenerator

import pytest
from httpx import AsyncClient

import hdfs_anomaly.app.api.main as api_main
from hdfs_anomaly.app.model.resources import InferenceResources
from tests.helpers import app_client


@pytest.fixture
async def client(
    monkeypatch: pytest.MonkeyPatch,
    fake_resources: InferenceResources,
) -> AsyncGenerator[AsyncClient]:
    monkeypatch.setattr(api_main, "load_resources", lambda: fake_resources)

    async with app_client() as client:
        yield client
