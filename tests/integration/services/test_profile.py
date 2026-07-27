import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from hdfs_anomaly.app.core.exceptions import (
    AdminSelfModificationError,
    DuplicateEmailError,
    InvalidCredentialsError,
    ProfileVersionConflictError,
)
from hdfs_anomaly.app.models.profile import Role, Status
from hdfs_anomaly.app.schemas.profile import (
    AdminProfileStatusUpdateRequest,
    EmailChangeRequest,
)
from hdfs_anomaly.app.services.profile import ProfileService
from tests.helpers import add_profile


async def test_profile_service_register_normalizes_email_and_rejects_duplicate(
    session: AsyncSession,
) -> None:
    service = ProfileService(session)

    profile_id = await service.register(email="  User@Mail.COM  ", password="123456")
    profile = await service.repository.get_by_id(profile_id=profile_id)

    assert profile is not None
    assert profile.email == "user@mail.com"
    assert profile.password != "123456"

    with pytest.raises(DuplicateEmailError):
        await service.register(email="user@mail.com", password="123456")


async def test_profile_service_authenticate_requires_active_profile_and_password(
    session: AsyncSession,
) -> None:
    service = ProfileService(session)
    inactive = await add_profile(session, email="inactive@mail.com")
    active = await add_profile(session, email="active@mail.com", status=Status.ACTIVE)
    await session.commit()

    with pytest.raises(InvalidCredentialsError):
        await service.authenticate(email=inactive.email, password="123456")

    with pytest.raises(InvalidCredentialsError):
        await service.authenticate(email=active.email, password="wrong-password")

    authenticated = await service.authenticate(email="  ACTIVE@MAIL.COM  ", password="123456")

    assert authenticated.id == active.id


async def test_profile_service_change_email_increments_version(
    session: AsyncSession,
) -> None:
    profile = await add_profile(session, email="user@mail.com", status=Status.ACTIVE)
    await session.commit()
    service = ProfileService(session)

    updated = await service.change_email(
        profile=profile,
        request=EmailChangeRequest(
            new_email="new@mail.com",
            current_password="123456",
            version=0,
        ),
    )

    assert updated.email == "new@mail.com"
    assert updated.version == 1

    with pytest.raises(ProfileVersionConflictError):
        await service.change_email(
            profile=updated,
            request=EmailChangeRequest(
                new_email="another@mail.com",
                current_password="123456",
                version=0,
            ),
        )


async def test_profile_service_admin_cannot_change_own_status(
    session: AsyncSession,
) -> None:
    admin = await add_profile(
        session,
        email="admin@mail.com",
        status=Status.ACTIVE,
        role=Role.ADMIN,
    )
    await session.commit()
    service = ProfileService(session)

    with pytest.raises(AdminSelfModificationError):
        await service.change_profile_status(
            admin_profile=admin,
            profile_id=admin.id,
            request=AdminProfileStatusUpdateRequest(status=Status.INACTIVE, version=0),
        )
