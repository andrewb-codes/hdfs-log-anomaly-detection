from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from hdfs_anomaly.app.core.exceptions import ForbiddenError, UnauthorizedError
from hdfs_anomaly.app.core.security import InvalidTokenError, decode_access_token
from hdfs_anomaly.app.db.session import get_db_session
from hdfs_anomaly.app.model.resources import InferenceResources
from hdfs_anomaly.app.models.profile import Profile, Role, Status
from hdfs_anomaly.app.repositories.profile import ProfileRepository
from hdfs_anomaly.app.services.history import HistoryService
from hdfs_anomaly.app.services.model import ModelService
from hdfs_anomaly.app.services.profile import ProfileService

bearer_scheme = HTTPBearer(auto_error=False)

resources: InferenceResources | None = None


def get_resources() -> InferenceResources:
    if resources is None:
        raise RuntimeError("inference resources are not loaded")
    return resources


def get_profile_service(session: AsyncSession = Depends(get_db_session)) -> ProfileService:
    return ProfileService(session)


def get_history_service(session: AsyncSession = Depends(get_db_session)) -> HistoryService:
    return HistoryService(session)


def get_model_service(
    history_service: HistoryService = Depends(get_history_service),
    resources: InferenceResources = Depends(get_resources),
) -> ModelService:
    return ModelService(history_service, resources)


async def get_current_profile(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> Profile:
    if credentials is None:
        raise UnauthorizedError()

    try:
        payload = decode_access_token(str(credentials.credentials))
        profile_id = int(payload["sub"])
    except (InvalidTokenError, KeyError, ValueError) as exc:
        raise UnauthorizedError() from exc

    repository = ProfileRepository(session)
    profile = await repository.get_by_id(profile_id=profile_id)

    if profile is None or profile.status != Status.ACTIVE:
        raise UnauthorizedError()

    return profile


def require_admin(profile: Profile = Depends(get_current_profile)) -> Profile:
    if profile.role != Role.ADMIN:
        raise ForbiddenError()

    return profile
