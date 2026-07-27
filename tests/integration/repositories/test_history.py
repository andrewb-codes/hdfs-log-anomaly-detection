from sqlalchemy.ext.asyncio import AsyncSession

from hdfs_anomaly.app.repositories.history import HistoryRepository
from tests.helpers import add_history_item, add_profile


async def test_history_repository_saves_and_lists_profile_history(
    session: AsyncSession,
) -> None:
    profile = await add_profile(session, email="user@mail.com")
    other_profile = await add_profile(session, email="other@mail.com")
    repository = HistoryRepository(session)

    first = await repository.save_request(
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
        error_message=None,
    )
    await add_history_item(session, profile_id=other_profile.id, block_id="other_blk")

    items = await repository.list_profile_history(profile_id=profile.id, limit=10, offset=0)

    assert items == [first]
    assert items[0].block_id == "blk_1"


async def test_history_repository_lists_all_history_with_pagination(
    session: AsyncSession,
) -> None:
    profile = await add_profile(session, email="user@mail.com")
    await add_history_item(session, profile_id=profile.id, block_id="blk_1")
    second = await add_history_item(session, profile_id=profile.id, block_id="blk_2")
    repository = HistoryRepository(session)

    items = await repository.list_all_history(limit=1, offset=0)

    assert items == [second]


async def test_history_repository_clears_profile_history_only(
    session: AsyncSession,
) -> None:
    profile = await add_profile(session, email="user@mail.com")
    other_profile = await add_profile(session, email="other@mail.com")
    await add_history_item(session, profile_id=profile.id, block_id="blk_1")
    await add_history_item(session, profile_id=other_profile.id, block_id="other_blk")
    repository = HistoryRepository(session)

    deleted_count = await repository.clear_profile_history(profile_id=profile.id)
    remaining_items = await repository.list_all_history(limit=10, offset=0)

    assert deleted_count == 1
    assert [item.block_id for item in remaining_items] == ["other_blk"]
