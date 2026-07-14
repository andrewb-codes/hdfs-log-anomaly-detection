from fastapi import APIRouter, Depends

from hdfs_anomaly.app.api.deps import (
    get_current_profile,
    get_model_service,
    get_resources,
    require_admin,
)
from hdfs_anomaly.app.model.resources import InferenceResources
from hdfs_anomaly.app.models.profile import Profile
from hdfs_anomaly.app.rate_limit.deps import rate_limit_user
from hdfs_anomaly.app.rate_limit.rules import MODEL_INFO_LIMIT, MODEL_PREDICT_LIMIT
from hdfs_anomaly.app.schemas.model import ModelInfoResponse, PredictRequest, PredictResponse
from hdfs_anomaly.app.services.model import ModelService

router = APIRouter(prefix="/api/v1/model", tags=["Model"])


@router.get(
    "/info",
    response_model=ModelInfoResponse,
    dependencies=[Depends(require_admin), Depends(rate_limit_user(MODEL_INFO_LIMIT))],
)
def model_info(resources: InferenceResources = Depends(get_resources)) -> ModelInfoResponse:
    """Return metadata for the currently loaded inference model."""
    return ModelInfoResponse(
        model_type="many_to_many_lstm",
        scoring_strategy=resources.scoring_strategy,
        threshold=resources.threshold,
        window_size=resources.window_size,
        stride=resources.stride,
        device=str(resources.device),
    )


@router.post("/predict", response_model=PredictResponse)
async def predict(
    request: PredictRequest,
    profile: Profile = Depends(get_current_profile),
    _: None = Depends(rate_limit_user(MODEL_PREDICT_LIMIT)),
    service: ModelService = Depends(get_model_service),
) -> PredictResponse:
    """Run anomaly inference for raw HDFS log lines and store request history."""
    return await service.predict(request=request, profile_id=profile.id)
