from fastapi import APIRouter, Depends, Response, status

from hdfs_anomaly.app.api.deps import get_profile_service
from hdfs_anomaly.app.core.config import settings
from hdfs_anomaly.app.rate_limit.deps import apply_rate_limit, get_rate_limit_service
from hdfs_anomaly.app.rate_limit.keys import (
    build_global_key,
    build_identifier_key,
    require_key_secret,
)
from hdfs_anomaly.app.rate_limit.rules import REGISTER_GLOBAL_LIMIT, REGISTER_IDENTIFIER_LIMIT
from hdfs_anomaly.app.rate_limit.service import RateLimitService
from hdfs_anomaly.app.schemas.auth import RegistrationRequest, RegistrationResponse
from hdfs_anomaly.app.services.profile import ProfileService

router = APIRouter(prefix="/api/v1/registration", tags=["Registration"])


@router.post("", response_model=RegistrationResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegistrationRequest,
    response: Response,
    rate_limit_service: RateLimitService = Depends(get_rate_limit_service),
    service: ProfileService = Depends(get_profile_service),
) -> RegistrationResponse:
    await apply_rate_limit(
        rule=REGISTER_GLOBAL_LIMIT,
        key_factory=lambda: build_global_key(scope=REGISTER_GLOBAL_LIMIT.scope),
        response=response,
        service=rate_limit_service,
    )
    await apply_rate_limit(
        rule=REGISTER_IDENTIFIER_LIMIT,
        key_factory=lambda: build_identifier_key(
            scope=REGISTER_IDENTIFIER_LIMIT.scope,
            identifier_kind="identifier",
            identifier=str(request.email),
            secret=require_key_secret(settings.rate_limit_key_secret),
        ),
        response=response,
        service=rate_limit_service,
    )

    profile_id = await service.register(email=str(request.email), password=request.password)

    return RegistrationResponse(id=profile_id)
