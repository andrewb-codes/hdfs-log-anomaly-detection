from httpx import AsyncClient
from sqlalchemy import text

from hdfs_anomaly.app.db.session import AsyncSessionLocal


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


async def register_and_login(
    client: AsyncClient, email: str = "user@mail.com", password: str = "123456"
) -> str:
    response = await client.post(
        "/api/v1/registration",
        json={"email": email, "password": password},
    )
    profile_id = int(response.json()["id"])

    await activate_profile(profile_id)

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )

    return str(response.json()["access_token"])


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
