from fastapi import APIRouter, Depends, status

from hdfs_anomaly.app.api.deps import get_profile_service
from hdfs_anomaly.app.schemas.auth import RegistrationRequest, RegistrationResponse
from hdfs_anomaly.app.services.profile import ProfileService

router = APIRouter(prefix="/api/v1/registration", tags=["Registration"])


@router.post("", response_model=RegistrationResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegistrationRequest,
    service: ProfileService = Depends(get_profile_service),
) -> RegistrationResponse:
    profile_id = await service.register(email=str(request.email), password=request.password)
    return RegistrationResponse(id=profile_id)
