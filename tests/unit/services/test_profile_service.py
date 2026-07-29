from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from hdfs_anomaly.app.core.exceptions import (
    AdminSelfModificationError,
    DuplicateEmailError,
    InvalidCredentialsError,
    InvalidCurrentPasswordError,
    ProfileNotFoundError,
    ProfileVersionConflictError,
    SameEmailError,
    SamePasswordError,
)
from hdfs_anomaly.app.models.profile import Profile, Role, Status
from hdfs_anomaly.app.repositories.profile import ProfileRepository
from hdfs_anomaly.app.schemas.profile import (
    AdminProfileRoleUpdateRequest,
    AdminProfileStatusUpdateRequest,
    EmailChangeRequest,
    PasswordChangeRequest,
)
from hdfs_anomaly.app.services.profile import ProfileService

pytestmark = pytest.mark.no_db


def make_profile(
    *,
    profile_id: int = 1,
    email: str = "user@mail.com",
    password: str = "hashed:123456",
    status: Status = Status.ACTIVE,
    role: Role = Role.USER,
    version: int = 0,
) -> Profile:
    return Profile(
        id=profile_id,
        email=email,
        password=password,
        status=status,
        role=role,
        version=version,
    )


def make_session() -> SimpleNamespace:
    return SimpleNamespace(commit=AsyncMock(), rollback=AsyncMock(), refresh=AsyncMock())


def make_profile_service(
    repository: SimpleNamespace | None = None,
    session: SimpleNamespace | None = None,
) -> ProfileService:
    service = ProfileService(cast(AsyncSession, cast(object, session or make_session())))
    service.repository = cast(ProfileRepository, cast(object, repository or SimpleNamespace()))
    return service


def make_email_request(
    *,
    new_email: str = "new@mail.com",
    current_password: str = "123456",
    version: int = 0,
) -> EmailChangeRequest:
    return EmailChangeRequest(
        new_email=new_email,
        current_password=current_password,
        version=version,
    )


def make_password_request(
    *,
    current_password: str = "123456",
    new_password: str = "new-secret",
    version: int = 0,
) -> PasswordChangeRequest:
    return PasswordChangeRequest(
        current_password=current_password,
        new_password=new_password,
        version=version,
    )


async def test_register_normalizes_email_hashes_password_and_commits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created_profile = make_profile(profile_id=10, email="user@mail.com")
    repository = SimpleNamespace(
        exists_by_email=AsyncMock(return_value=False),
        create=AsyncMock(return_value=created_profile),
    )
    session = make_session()
    service = make_profile_service(repository=repository, session=session)
    monkeypatch.setattr(
        "hdfs_anomaly.app.services.profile.hash_password",
        lambda password: f"hashed:{password}",
    )

    profile_id = await service.register(email="  User@Mail.COM  ", password="123456")

    repository.exists_by_email.assert_awaited_once_with(email="user@mail.com")
    repository.create.assert_awaited_once_with(
        email="user@mail.com",
        password_hash="hashed:123456",
    )
    session.commit.assert_awaited_once_with()
    assert profile_id == 10


async def test_register_rejects_existing_email_without_creating_profile() -> None:
    repository = SimpleNamespace(
        exists_by_email=AsyncMock(return_value=True),
        create=AsyncMock(),
    )
    session = make_session()
    service = make_profile_service(repository=repository, session=session)

    with pytest.raises(DuplicateEmailError):
        await service.register(email="user@mail.com", password="123456")

    repository.create.assert_not_awaited()
    session.commit.assert_not_awaited()


async def test_authenticate_normalizes_email_and_returns_active_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = make_profile(status=Status.ACTIVE)
    repository = SimpleNamespace(get_by_email=AsyncMock(return_value=profile))
    service = make_profile_service(repository=repository)
    monkeypatch.setattr("hdfs_anomaly.app.services.profile.verify_password", lambda *_: True)

    authenticated = await service.authenticate(email="  USER@MAIL.COM  ", password="123456")

    repository.get_by_email.assert_awaited_once_with(email="user@mail.com")
    assert authenticated is profile


async def test_authenticate_rejects_missing_profile() -> None:
    repository = SimpleNamespace(get_by_email=AsyncMock(return_value=None))
    service = make_profile_service(repository=repository)

    with pytest.raises(InvalidCredentialsError):
        await service.authenticate(email="user@mail.com", password="123456")


async def test_authenticate_rejects_inactive_profile() -> None:
    repository = SimpleNamespace(
        get_by_email=AsyncMock(return_value=make_profile(status=Status.INACTIVE))
    )
    service = make_profile_service(repository=repository)

    with pytest.raises(InvalidCredentialsError):
        await service.authenticate(email="user@mail.com", password="123456")


async def test_authenticate_rejects_invalid_password(monkeypatch: pytest.MonkeyPatch) -> None:
    repository = SimpleNamespace(get_by_email=AsyncMock(return_value=make_profile()))
    service = make_profile_service(repository=repository)
    monkeypatch.setattr("hdfs_anomaly.app.services.profile.verify_password", lambda *_: False)

    with pytest.raises(InvalidCredentialsError):
        await service.authenticate(email="user@mail.com", password="wrong")


async def test_change_email_updates_profile_version_and_refreshes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = make_profile(email="user@mail.com", version=2)
    repository = SimpleNamespace(exists_by_email=AsyncMock(return_value=False))
    session = make_session()
    service = make_profile_service(repository=repository, session=session)
    monkeypatch.setattr("hdfs_anomaly.app.services.profile.verify_password", lambda *_: True)

    updated = await service.change_email(
        profile=profile,
        request=make_email_request(new_email="New@Mail.com", version=2),
    )

    repository.exists_by_email.assert_awaited_once_with(email="new@mail.com")
    session.commit.assert_awaited_once_with()
    session.refresh.assert_awaited_once_with(profile)
    assert updated.email == "new@mail.com"
    assert updated.version == 3


async def test_change_email_rejects_version_conflict() -> None:
    service = make_profile_service()

    with pytest.raises(ProfileVersionConflictError):
        await service.change_email(
            profile=make_profile(version=2),
            request=make_email_request(version=1),
        )


async def test_change_email_rejects_invalid_current_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = make_profile_service()
    monkeypatch.setattr("hdfs_anomaly.app.services.profile.verify_password", lambda *_: False)

    with pytest.raises(InvalidCurrentPasswordError):
        await service.change_email(
            profile=make_profile(version=2),
            request=make_email_request(current_password="wrong", version=2),
        )


async def test_change_email_rejects_same_email(monkeypatch: pytest.MonkeyPatch) -> None:
    service = make_profile_service()
    monkeypatch.setattr("hdfs_anomaly.app.services.profile.verify_password", lambda *_: True)

    with pytest.raises(SameEmailError):
        await service.change_email(
            profile=make_profile(email="user@mail.com", version=2),
            request=make_email_request(new_email="USER@mail.com", version=2),
        )


async def test_change_email_rejects_duplicate_email(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = SimpleNamespace(exists_by_email=AsyncMock(return_value=True))
    service = make_profile_service(repository=repository)
    monkeypatch.setattr("hdfs_anomaly.app.services.profile.verify_password", lambda *_: True)

    with pytest.raises(DuplicateEmailError):
        await service.change_email(
            profile=make_profile(email="user@mail.com", version=2),
            request=make_email_request(new_email="taken@mail.com", version=2),
        )

    repository.exists_by_email.assert_awaited_once_with(email="taken@mail.com")


async def test_change_password_updates_hash_version_and_refreshes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = make_profile(version=1)
    session = make_session()
    service = make_profile_service(session=session)
    monkeypatch.setattr(
        "hdfs_anomaly.app.services.profile.verify_password",
        lambda password, _hash: password == "123456",
    )
    monkeypatch.setattr(
        "hdfs_anomaly.app.services.profile.hash_password",
        lambda password: f"hashed:{password}",
    )

    updated = await service.change_password(
        profile=profile,
        request=make_password_request(new_password="new-secret", version=1),
    )

    assert updated.password == "hashed:new-secret"
    assert updated.version == 2
    session.commit.assert_awaited_once_with()
    session.refresh.assert_awaited_once_with(profile)


async def test_change_password_rejects_version_conflict() -> None:
    service = make_profile_service()

    with pytest.raises(ProfileVersionConflictError):
        await service.change_password(
            profile=make_profile(version=1),
            request=make_password_request(version=0),
        )


async def test_change_password_rejects_invalid_current_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = make_profile_service()
    monkeypatch.setattr("hdfs_anomaly.app.services.profile.verify_password", lambda *_: False)

    with pytest.raises(InvalidCurrentPasswordError):
        await service.change_password(
            profile=make_profile(version=1),
            request=make_password_request(current_password="wrong", version=1),
        )


async def test_change_password_rejects_same_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = make_profile_service()
    monkeypatch.setattr("hdfs_anomaly.app.services.profile.verify_password", lambda *_: True)

    with pytest.raises(SamePasswordError):
        await service.change_password(
            profile=make_profile(version=1),
            request=make_password_request(new_password="123456", version=1),
        )


async def test_delete_profile_delegates_to_repository_and_commits() -> None:
    profile = make_profile()
    repository = SimpleNamespace(delete=AsyncMock())
    session = make_session()
    service = make_profile_service(repository=repository, session=session)

    await service.delete_profile(profile=profile)

    repository.delete.assert_awaited_once_with(profile=profile)
    session.commit.assert_awaited_once_with()


async def test_search_profiles_normalizes_pagination_and_trims_extra_item() -> None:
    first = make_profile(profile_id=1)
    second = make_profile(profile_id=2, email="user2@mail.com")
    repository = SimpleNamespace(search_profiles=AsyncMock(return_value=[first, second]))
    service = make_profile_service(repository=repository)

    items, has_next = await service.search_profiles(
        email_starts_with="user",
        role=Role.USER,
        status=Status.ACTIVE,
        page=0,
        page_size=1,
    )

    repository.search_profiles.assert_awaited_once_with(
        email_starts_with="user",
        role=Role.USER,
        status=Status.ACTIVE,
        limit=2,
        offset=0,
    )
    assert items == [first]
    assert has_next is True


async def test_admin_status_change_rejects_self_modification() -> None:
    admin = make_profile(profile_id=1, role=Role.ADMIN)
    service = make_profile_service()

    with pytest.raises(AdminSelfModificationError):
        await service.change_profile_status(
            admin_profile=admin,
            profile_id=admin.id,
            request=AdminProfileStatusUpdateRequest(status=Status.INACTIVE, version=0),
        )


async def test_admin_status_change_rejects_missing_profile() -> None:
    admin = make_profile(profile_id=1, role=Role.ADMIN)
    repository = SimpleNamespace(get_by_id=AsyncMock(return_value=None))
    service = make_profile_service(repository=repository)

    with pytest.raises(ProfileNotFoundError):
        await service.change_profile_status(
            admin_profile=admin,
            profile_id=2,
            request=AdminProfileStatusUpdateRequest(status=Status.INACTIVE, version=0),
        )


async def test_admin_status_change_rejects_version_conflict() -> None:
    admin = make_profile(profile_id=1, role=Role.ADMIN)
    repository = SimpleNamespace(get_by_id=AsyncMock(return_value=make_profile(profile_id=2, version=2)))
    service = make_profile_service(repository=repository)

    with pytest.raises(ProfileVersionConflictError):
        await service.change_profile_status(
            admin_profile=admin,
            profile_id=2,
            request=AdminProfileStatusUpdateRequest(status=Status.INACTIVE, version=1),
        )


async def test_admin_status_and_role_changes_update_profile_and_refresh() -> None:
    admin = make_profile(profile_id=1, role=Role.ADMIN)
    target = make_profile(profile_id=2, status=Status.INACTIVE, role=Role.USER, version=3)
    repository = SimpleNamespace(get_by_id=AsyncMock(return_value=target))
    session = make_session()
    service = make_profile_service(repository=repository, session=session)

    updated_status = await service.change_profile_status(
        admin_profile=admin,
        profile_id=2,
        request=AdminProfileStatusUpdateRequest(status=Status.ACTIVE, version=3),
    )
    updated_role = await service.change_profile_role(
        admin_profile=admin,
        profile_id=2,
        request=AdminProfileRoleUpdateRequest(role=Role.ADMIN, version=4),
    )

    assert updated_status.status == Status.ACTIVE
    assert updated_role.role == Role.ADMIN
    assert target.version == 5
    assert session.commit.await_count == 2
    assert session.refresh.await_count == 2
