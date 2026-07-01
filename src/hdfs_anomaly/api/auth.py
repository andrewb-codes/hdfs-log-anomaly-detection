import hmac
import os
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

load_dotenv()


def _get_required_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or value == "":
        raise RuntimeError(f"{name} environment variable is required")
    return value


SECRET_KEY = _get_required_env("API_SECRET_KEY")
ALGORITHM = _get_required_env("API_JWT_ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(_get_required_env("API_ACCESS_TOKEN_EXPIRE_MINUTES"))

ADMIN_USERNAME = _get_required_env("API_ADMIN_USERNAME")
ADMIN_PASSWORD = _get_required_env("API_ADMIN_PASSWORD")

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
