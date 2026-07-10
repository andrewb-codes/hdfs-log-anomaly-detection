import asyncio

from hdfs_anomaly.app.core.config import settings
from hdfs_anomaly.app.core.security import hash_password
from hdfs_anomaly.app.db.session import AsyncSessionLocal
from hdfs_anomaly.app.models.profile import Profile, Role, Status
from hdfs_anomaly.app.repositories.profile import ProfileRepository


async def seed_admin(repository: ProfileRepository) -> None:
    if not settings.bootstrap_admin_enabled:
        return

    email = settings.bootstrap_admin_email
    password = settings.bootstrap_admin_password

    if email is None or password is None:
        raise RuntimeError(
            "BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD are required when admin user is enabled"
        )

    normalized_email = email.strip().lower()
    existing = await repository.get_by_email(email=normalized_email)

    if existing is not None:
        if existing.role != Role.ADMIN:
            raise RuntimeError(
                f"Profile {normalized_email} exists but is not an admin"
            )
        return

    repository.session.add(
        Profile(
            email=normalized_email,
            password=hash_password(password),
            status=Status.ACTIVE,
            role=Role.ADMIN,
        )
    )
    
    
async def seed_demo_user(repository: ProfileRepository) -> None:
    if not settings.demo_user_enabled:
        return
    
    email = settings.demo_email
    password = settings.demo_password

    if email is None or password is None:
        raise RuntimeError("DEMO_EMAIL and DEMO_PASSWORD are required when demo user is enabled")

    normalized_email = email.strip().lower()
    
    if await repository.exists_by_email(email=normalized_email):
        return

    profile = Profile(
        email=email,
        password=hash_password(password),
        status=Status.ACTIVE,
        role=Role.USER,
    )

    repository.session.add(profile)


async def main() -> None:
    async with AsyncSessionLocal() as session:
        profile_repository = ProfileRepository(session)
        await seed_admin(profile_repository)
        await seed_demo_user(profile_repository)
        await session.commit()


if __name__ == "__main__":
    asyncio.run(main())
