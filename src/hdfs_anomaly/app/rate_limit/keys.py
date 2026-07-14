import hashlib
import hmac

from hdfs_anomaly.app.rate_limit.scopes import RateLimitScope

KEY_NAMESPACE = "rate-limit"


def normalize_identifier(identifier: str) -> str:
    return identifier.strip().lower()


def hash_identifier(identifier: str, secret: str) -> str:
    normalized_identifier = normalize_identifier(identifier)
    return hmac.new(
        key=secret.encode("utf-8"),
        msg=normalized_identifier.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()


def build_user_key(*, scope: RateLimitScope, user_id: int) -> str:
    return f"{KEY_NAMESPACE}:{scope}:user:{user_id}"


def build_identifier_key(
    *,
    scope: RateLimitScope,
    identifier_kind: str,
    identifier: str,
    secret: str,
) -> str:
    identifier_hash = hash_identifier(identifier=identifier, secret=secret)
    return f"{KEY_NAMESPACE}:{scope}:{identifier_kind}:{identifier_hash}"


def build_global_key(*, scope: RateLimitScope) -> str:
    return f"{KEY_NAMESPACE}:{scope}:global"


def require_key_secret(secret: str | None) -> str:
    if not secret:
        raise RuntimeError("RATE_LIMIT_KEY_SECRET is required to build rate limit identifier keys")

    return secret
