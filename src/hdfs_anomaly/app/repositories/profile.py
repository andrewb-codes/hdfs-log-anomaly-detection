from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hdfs_anomaly.app.models.profile import Profile, Role, Status


class ProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, *, email: str, password_hash: str) -> Profile:
        profile = Profile(email=email, password=password_hash)
        self.session.add(profile)
        await self.session.flush()
        return profile

    async def get_by_email(self, *, email: str) -> Profile | None:
        query = select(Profile).where(Profile.email == email)
        result = await self.session.scalar(query)
        return cast(Profile | None, result)

    async def exists_by_email(self, *, email: str) -> bool:
        result = await self.get_by_email(email=email)
        return result is not None

    async def get_by_id(self, *, profile_id: int) -> Profile | None:
        return cast(Profile | None, await self.session.get(Profile, profile_id))

    async def delete(self, *, profile: Profile) -> None:
        await self.session.delete(profile)

    async def search_profiles(
        self,
        *,
        email_starts_with: str | None,
        role: Role | None,
        status: Status | None,
        limit: int,
        offset: int,
    ) -> list[Profile]:
        query = select(Profile).order_by(Profile.id.asc()).limit(limit).offset(offset)

        if email_starts_with:
            query = query.where(Profile.email.ilike(f"{email_starts_with}%"))

        if role is not None:
            query = query.where(Profile.role == role)

        if status is not None:
            query = query.where(Profile.status == status)

        result = await self.session.scalars(query)
        return list(result)
