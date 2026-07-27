from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from hdfs_anomaly.app.core.security import hash_password
from hdfs_anomaly.app.db.session import AsyncSessionLocal
from hdfs_anomaly.app.models.history import RequestHistory
from hdfs_anomaly.app.models.profile import Profile, Role, Status


async def add_profile(
    session: AsyncSession,
    *,
    email: str,
    password: str = "123456",
    status: Status = Status.INACTIVE,
    role: Role = Role.USER,
) -> Profile:
    profile = Profile(
        email=email,
        password=hash_password(password),
        status=status,
        role=role,
    )
    session.add(profile)
    await session.flush()
    return profile


async def add_history_item(
    session: AsyncSession,
    *,
    profile_id: int,
    block_id: str | None = "blk_1",
    status_code: int = 200,
    processing_ms: float = 10.0,
    num_log_lines: int | None = 2,
    num_events: int | None = 3,
    num_windows: int | None = 1,
    score: float | None = 0.7,
    threshold: float | None = 0.5,
    is_anomaly: bool | None = True,
    error_message: str | None = None,
) -> RequestHistory:
    item = RequestHistory(
        profile_id=profile_id,
        block_id=block_id,
        status_code=status_code,
        processing_ms=processing_ms,
        num_log_lines=num_log_lines,
        num_events=num_events,
        num_windows=num_windows,
        score=score,
        threshold=threshold,
        is_anomaly=is_anomaly,
        error_message=error_message,
    )
    session.add(item)
    await session.flush()
    return item


async def activate_profile(profile_id: int) -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(
            text(
                """
                UPDATE profile
                SET status = 'ACTIVE'
                WHERE id = :profile_id
                """
            ),
            {"profile_id": profile_id},
        )
        await session.commit()


async def make_admin(profile_id: int) -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(
            text(
                """
                UPDATE profile
                SET role = 'ADMIN'
                WHERE id = :profile_id
                """
            ),
            {"profile_id": profile_id},
        )
        await session.commit()
