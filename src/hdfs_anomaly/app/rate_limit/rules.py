from dataclasses import dataclass
from typing import Literal

from hdfs_anomaly.app.rate_limit.scopes import RateLimitScope

RateLimitFailureMode = Literal["open", "closed"]


@dataclass(frozen=True)
class RateLimitRule:
    scope: RateLimitScope
    limit: str
    failure_mode: RateLimitFailureMode = "open"


REGISTER_IDENTIFIER_LIMIT = RateLimitRule(
    scope=RateLimitScope.REGISTER_IDENTIFIER,
    limit="3 per hour",
    failure_mode="open",
)

REGISTER_GLOBAL_LIMIT = RateLimitRule(
    scope=RateLimitScope.REGISTER_GLOBAL,
    limit="30 per hour",
    failure_mode="open",
)

LOGIN_ACCOUNT_LIMIT = RateLimitRule(
    scope=RateLimitScope.LOGIN_ACCOUNT,
    limit="5 per minute",
    failure_mode="open",
)

LOGIN_GLOBAL_LIMIT = RateLimitRule(
    scope=RateLimitScope.LOGIN_GLOBAL,
    limit="60 per minute",
    failure_mode="open",
)

PROFILE_READ_LIMIT = RateLimitRule(
    scope=RateLimitScope.PROFILE_READ,
    limit="120 per minute",
    failure_mode="open",
)

PROFILE_WRITE_LIMIT = RateLimitRule(
    scope=RateLimitScope.PROFILE_WRITE,
    limit="30 per minute",
    failure_mode="open",
)

HISTORY_READ_LIMIT = RateLimitRule(
    scope=RateLimitScope.HISTORY_READ,
    limit="120 per minute",
    failure_mode="open",
)

HISTORY_WRITE_LIMIT = RateLimitRule(
    scope=RateLimitScope.HISTORY_WRITE,
    limit="30 per minute",
    failure_mode="open",
)

MODEL_INFO_LIMIT = RateLimitRule(
    scope=RateLimitScope.MODEL_INFO,
    limit="60 per minute",
    failure_mode="open",
)

MODEL_PREDICT_LIMIT = RateLimitRule(
    scope=RateLimitScope.MODEL_PREDICT,
    limit="30 per minute",
    failure_mode="open",
)

ADMIN_READ_LIMIT = RateLimitRule(
    scope=RateLimitScope.ADMIN_READ,
    limit="120 per minute",
    failure_mode="open",
)

ADMIN_WRITE_LIMIT = RateLimitRule(
    scope=RateLimitScope.ADMIN_WRITE,
    limit="30 per minute",
    failure_mode="open",
)
