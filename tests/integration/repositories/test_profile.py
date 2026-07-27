from sqlalchemy.ext.asyncio import AsyncSession

from hdfs_anomaly.app.models.profile import Role, Status
from hdfs_anomaly.app.repositories.profile import ProfileRepository
from tests.helpers import add_profile


async def test_profile_repository_create_and_get_by_email(session: AsyncSession) -> None:
    repository = ProfileRepository(session)

    profile = await repository.create(
        email="user@mail.com",
        password_hash="password-hash",
    )

    found = await repository.get_by_email(email="user@mail.com")

    assert found is profile
    assert found.email == "user@mail.com"
    assert found.status == Status.INACTIVE
    assert found.role == Role.USER


async def test_profile_repository_search_filters_and_paginates(
    session: AsyncSession,
) -> None:
    await add_profile(
        session,
        email="admin@mail.com",
        status=Status.ACTIVE,
        role=Role.ADMIN,
    )
    await add_profile(session, email="alice@mail.com", status=Status.ACTIVE)
    await add_profile(session, email="bob@mail.com")
    repository = ProfileRepository(session)

    active_profiles = await repository.search_profiles(
        email_starts_with=None,
        role=None,
        status=Status.ACTIVE,
        limit=10,
        offset=0,
    )
    alice_profiles = await repository.search_profiles(
        email_starts_with="ali",
        role=None,
        status=None,
        limit=10,
        offset=0,
    )
    second_page = await repository.search_profiles(
        email_starts_with=None,
        role=None,
        status=None,
        limit=1,
        offset=1,
    )

    assert [profile.email for profile in active_profiles] == [
        "admin@mail.com",
        "alice@mail.com",
    ]
    assert [profile.email for profile in alice_profiles] == ["alice@mail.com"]
    assert [profile.email for profile in second_page] == ["alice@mail.com"]


async def test_profile_repository_delete_removes_profile(session: AsyncSession) -> None:
    profile = await add_profile(session, email="user@mail.com")
    repository = ProfileRepository(session)

    await repository.delete(profile=profile)
    await session.flush()

    assert await repository.get_by_id(profile_id=profile.id) is None
