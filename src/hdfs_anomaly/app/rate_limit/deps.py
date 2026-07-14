from collections.abc import Awaitable, Callable
from typing import Annotated, cast

from fastapi import Depends, Response
from fastapi.requests import Request

from hdfs_anomaly.app.api.deps import get_current_profile
from hdfs_anomaly.app.models.profile import Profile
from hdfs_anomaly.app.rate_limit.exceptions import RateLimitExceededError
from hdfs_anomaly.app.rate_limit.keys import build_user_key
from hdfs_anomaly.app.rate_limit.rules import RateLimitRule
from hdfs_anomaly.app.rate_limit.service import RateLimitService


def get_rate_limit_service(request: Request) -> RateLimitService:
    return cast(RateLimitService, request.app.state.rate_limiter)


async def apply_rate_limit(
    *,
    rule: RateLimitRule,
    key_factory: Callable[[], str],
    response: Response,
    service: RateLimitService,
) -> None:
    if not service.enabled:
        return

    result = await service.hit(rule=rule, key=key_factory())

    if result.limit is not None:
        response.headers["X-RateLimit-Limit"] = str(result.limit)

    if result.remaining is not None:
        response.headers["X-RateLimit-Remaining"] = str(result.remaining)

    if result.reset_at is not None:
        response.headers["X-RateLimit-Reset"] = str(result.reset_at)

    if result.allowed:
        return

    raise RateLimitExceededError(retry_after=result.retry_after)


def rate_limit_user(rule: RateLimitRule) -> Callable[..., Awaitable[None]]:
    async def dependency(
        response: Response,
        profile: Annotated[Profile, Depends(get_current_profile)],
        service: Annotated[RateLimitService, Depends(get_rate_limit_service)],
    ) -> None:
        await apply_rate_limit(
            rule=rule,
            key_factory=lambda: build_user_key(scope=rule.scope, user_id=profile.id),
            response=response,
            service=service,
        )

    return dependency
