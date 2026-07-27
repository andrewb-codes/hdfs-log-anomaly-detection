from sqlalchemy.ext.asyncio import AsyncSession

from hdfs_anomaly.app.services.history import HistoryService
from tests.helpers import add_history_item, add_profile


async def test_history_service_saves_history_item(session: AsyncSession) -> None:
    profile = await add_profile(session, email="user@mail.com")
    await session.commit()
    service = HistoryService(session)

    item = await service.save_history_item(
        profile_id=profile.id,
        block_id="blk_1",
        status_code=200,
        processing_ms=10.0,
        num_log_lines=2,
        num_events=3,
        num_windows=1,
        score=0.7,
        threshold=0.5,
        is_anomaly=True,
    )

    assert item.id is not None
    assert item.block_id == "blk_1"
    assert item.profile_id == profile.id


async def test_history_service_lists_profile_history_with_has_next(
    session: AsyncSession,
) -> None:
    profile = await add_profile(session, email="user@mail.com")
    await add_history_item(session, profile_id=profile.id, block_id="blk_1")
    await add_history_item(session, profile_id=profile.id, block_id="blk_2")
    await session.commit()
    service = HistoryService(session)

    items, has_next = await service.list_profile_history(
        page=1,
        page_size=1,
        profile_id=profile.id,
    )

    assert len(items) == 1
    assert items[0].block_id == "blk_2"
    assert has_next is True


async def test_history_service_clear_all_history(session: AsyncSession) -> None:
    profile = await add_profile(session, email="user@mail.com")
    await add_history_item(session, profile_id=profile.id, block_id="blk_1")
    await add_history_item(session, profile_id=profile.id, block_id="blk_2")
    await session.commit()
    service = HistoryService(session)

    deleted_count = await service.clear_all_history()
    items, has_next = await service.list_all_history(page=1, page_size=10)

    assert deleted_count == 2
    assert items == []
    assert has_next is False
