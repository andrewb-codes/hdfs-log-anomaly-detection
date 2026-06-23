import hmac
import os
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

SECRET_KEY = os.getenv("API_SECRET_KEY", "dev-secret-key")
ALGORITHM = os.getenv("API_JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("API_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

ADMIN_USERNAME = os.getenv("API_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("API_ADMIN_PASSWORD", "admin")

bearer_scheme = HTTPBearer()


def authenticate_admin(username: str, password: str) -> bool:
    """Return whether credentials match configured admin credentials."""
    username_matches = hmac.compare_digest(username, ADMIN_USERNAME)
    password_matches = hmac.compare_digest(password, ADMIN_PASSWORD)
    return username_matches and password_matches


def create_access_token(subject: str, role: str) -> str:
    """Create a signed JWT access token for an authenticated API user."""
    expires_at = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": subject, "role": role, "exp": expires_at}
    return cast(str, jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM))


def require_admin(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict[str, Any]:
    """Validate bearer JWT credentials and require the admin role."""
    try:
        payload = cast(
            dict[str, Any], jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        )
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="invalid token") from exc

    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="admin role required")

    return payload
