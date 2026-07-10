from datetime import UTC, datetime, timedelta
from typing import Any, cast

from jose import JWTError, jwt
from pwdlib import PasswordHash

from hdfs_anomaly.app.core.config import settings

password_hash = PasswordHash.recommended()


class InvalidTokenError(Exception):
    pass


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def create_access_token(*, profile_id: int, role: str) -> str:
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=settings.jwt_ttl_minutes)

    payload = {
        "sub": str(profile_id),
        "role": role,
        "iat": now,
        "exp": expires_at,
    }

    return cast(
        str,
        jwt.encode(
            payload,
            settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
        ),
    )


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return cast(
            dict[str, Any],
            jwt.decode(
                token,
                settings.jwt_secret,
                algorithms=[settings.jwt_algorithm],
            ),
        )
    except JWTError as exc:
        raise InvalidTokenError from exc
