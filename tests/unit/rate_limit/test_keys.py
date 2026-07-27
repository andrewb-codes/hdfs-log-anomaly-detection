import pytest

from hdfs_anomaly.app.rate_limit.keys import (
    build_global_key,
    build_identifier_key,
    build_user_key,
    hash_identifier,
    normalize_identifier,
)
from hdfs_anomaly.app.rate_limit.scopes import RateLimitScope

pytestmark = pytest.mark.no_db


def test_normalize_identifier_strips_and_lowercases() -> None:
    assert normalize_identifier("  User@Mail.COM  ") == "user@mail.com"


def test_hash_identifier_is_stable_for_normalized_identifier() -> None:
    first = hash_identifier(identifier="User@Mail.COM", secret="secret")
    second = hash_identifier(identifier="  user@mail.com  ", secret="secret")

    assert first == second


def test_hash_identifier_changes_with_secret() -> None:
    first = hash_identifier(identifier="user@mail.com", secret="secret-1")
    second = hash_identifier(identifier="user@mail.com", secret="secret-2")

    assert first != second


def test_identifier_key_does_not_contain_raw_identifier() -> None:
    key = build_identifier_key(
        scope=RateLimitScope.LOGIN_ACCOUNT,
        identifier_kind="account",
        identifier="user@mail.com",
        secret="secret",
    )

    assert key.startswith("rate-limit:login_account:account:")
    assert "user@mail.com" not in key


def test_user_key_contains_user_id_and_scope() -> None:
    key = build_user_key(scope=RateLimitScope.PROFILE_READ, user_id=123)

    assert key == "rate-limit:profile_read:user:123"


def test_global_key_contains_scope() -> None:
    key = build_global_key(scope=RateLimitScope.LOGIN_GLOBAL)

    assert key == "rate-limit:login_global:global"
