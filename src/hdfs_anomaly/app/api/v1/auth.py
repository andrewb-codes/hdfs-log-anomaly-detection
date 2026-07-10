from fastapi import APIRouter, Depends

from hdfs_anomaly.app.api.deps import get_profile_service
from hdfs_anomaly.app.core.config import settings
from hdfs_anomaly.app.core.security import create_access_token
from hdfs_anomaly.app.schemas.auth import LoginRequest, TokenResponse
from hdfs_anomaly.app.services.profile import ProfileService

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest, service: ProfileService = Depends(get_profile_service)
) -> TokenResponse:
    profile = await service.authenticate(email=str(request.email), password=request.password)

    access_token = create_access_token(profile_id=profile.id, role=profile.role.value)

    return TokenResponse(access_token=access_token, expires_in=settings.jwt_ttl_minutes * 60)
