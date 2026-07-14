from httpx import AsyncClient
from sqlalchemy import text

from hdfs_anomaly.app.db.session import AsyncSessionLocal
from hdfs_anomaly.app.rate_limit.rules import RateLimitRule
from hdfs_anomaly.app.rate_limit.service import RateLimitResult


class FakeRateLimitService:
    enabled = True

    def __init__(self, *, denied_scope: str | None = None) -> None:
        self.denied_scope = denied_scope
        self.calls: list[tuple[RateLimitRule, str]] = []

    async def hit(self, *, rule: RateLimitRule, key: str, cost: int = 1) -> RateLimitResult:
        self.calls.append((rule, key))

        allowed = rule.scope != self.denied_scope

        return RateLimitResult(
            allowed=allowed,
            limit=1,
            remaining=0 if not allowed else 1,
            reset_at=123,
            retry_after=42,
        )


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
