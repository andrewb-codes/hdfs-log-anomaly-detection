import pytest

from hdfs_anomaly.app.rate_limit.rules import RateLimitRule
from hdfs_anomaly.app.rate_limit.scopes import RateLimitScope
from hdfs_anomaly.app.rate_limit.service import RateLimitService

pytestmark = pytest.mark.no_db


async def test_disabled_rate_limit_service_allows_request() -> None:
    service = RateLimitService(enabled=False)
    rule = RateLimitRule(scope=RateLimitScope.LOGIN_GLOBAL, limit="1 per minute")

    result = await service.hit(rule=rule, key="rate-limit:login_global:global")

    assert result.allowed is True
    assert result.limit is None
    assert result.remaining is None
    assert result.reset_at is None


async def test_rate_limit_service_fails_open_when_limiter_is_unavailable() -> None:
    service = RateLimitService(enabled=True, limiter=None)
    rule = RateLimitRule(
        scope=RateLimitScope.LOGIN_GLOBAL,
        limit="1 per minute",
        failure_mode="open",
    )

    result = await service.hit(rule=rule, key="rate-limit:login_global:global")

    assert result.allowed is True


async def test_rate_limit_service_fails_closed_when_limiter_is_unavailable() -> None:
    service = RateLimitService(enabled=True, limiter=None)
    rule = RateLimitRule(
        scope=RateLimitScope.LOGIN_GLOBAL,
        limit="1 per minute",
        failure_mode="closed",
    )

    result = await service.hit(rule=rule, key="rate-limit:login_global:global")

    assert result.allowed is False
    assert result.retry_after == 1
