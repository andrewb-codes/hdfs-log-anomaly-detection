import time

from fastapi import HTTPException
from fastapi.concurrency import run_in_threadpool

from hdfs_anomaly.app.model.inference import run_inference
from hdfs_anomaly.app.model.resources import InferenceResources
from hdfs_anomaly.app.schemas.model import PredictRequest, PredictResponse
from hdfs_anomaly.app.services.history import HistoryService


class ModelService:
    def __init__(
        self,
        history_service: HistoryService,
        resources: InferenceResources,
    ) -> None:
        self.history_service = history_service
        self.resources = resources

    async def predict(self, *, request: PredictRequest, profile_id: int) -> PredictResponse:
        started_at = time.perf_counter()

        try:
            response = await run_in_threadpool(run_inference, request, self.resources)
        except Exception as exc:
            processing_ms = (time.perf_counter() - started_at) * 1000

            await self.history_service.save_history_item(
                profile_id=profile_id,
                block_id=request.block_id,
                status_code=422,
                processing_ms=processing_ms,
                num_log_lines=len(request.log_lines),
                error_message="model couldn't process data",
            )
            raise HTTPException(status_code=422, detail="model couldn`t process data") from exc

        processing_ms = (time.perf_counter() - started_at) * 1000

        await self.history_service.save_history_item(
            profile_id=profile_id,
            block_id=response.block_id,
            status_code=200,
            processing_ms=processing_ms,
            num_log_lines=response.num_log_lines,
            num_events=response.num_events,
            num_windows=response.num_windows,
            score=response.score,
            threshold=response.threshold,
            is_anomaly=response.is_anomaly,
        )

        return response
