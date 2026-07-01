import hmac
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from hdfs_anomaly.api.config import settings

bearer_scheme = HTTPBearer()


def authenticate_admin(username: str, password: str) -> bool:
    """Return whether credentials match configured admin credentials."""
    username_matches = hmac.compare_digest(username, settings.api_admin_username)
    password_matches = hmac.compare_digest(password, settings.api_admin_password)
    return username_matches and password_matches


def create_access_token(subject: str, role: str) -> str:
    """Create a signed JWT access token for an authenticated API user."""
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.api_access_token_expire_minutes)
    payload = {"sub": subject, "role": role, "exp": expires_at}
    return cast(
        str, jwt.encode(payload, settings.api_secret_key, algorithm=settings.api_jwt_algorithm)
    )


def require_admin(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict[str, Any]:
    """Validate bearer JWT credentials and require the admin role."""
    try:
        payload = cast(
            dict[str, Any],
            jwt.decode(
                credentials.credentials,
                settings.api_secret_key,
                algorithms=[settings.api_jwt_algorithm],
            ),
        )
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="invalid token") from exc

    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="admin role required")

    return payload
