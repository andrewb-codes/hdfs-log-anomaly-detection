from types import SimpleNamespace

import pytest
from sqlalchemy import text

from hdfs_anomaly.app.db.session import AsyncSessionLocal


@pytest.fixture(autouse=True)
async def clean_db(request: pytest.FixtureRequest) -> None:
    if request.node.get_closest_marker("no_db"):
        return

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
