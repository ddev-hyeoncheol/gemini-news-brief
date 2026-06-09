from fastapi import APIRouter, Depends, HTTPException, Response, status

from src.core.logger import get_logger
from src.models.schemas.batch import (
    BatchLayer,
    BatchPipelineResponse,
    BatchRequest,
    BatchResponse,
    BatchTarget,
    VALID_BATCH_COMBINATIONS,
)
from src.worker.services.batch import BatchService, get_batch_service

logger = get_logger(__name__)

router = APIRouter(prefix="/batch", tags=["batch"])


@router.post(
    "/run",
    response_model=BatchPipelineResponse,
    response_model_exclude_none=True,
    responses={
        status.HTTP_200_OK: {"description": "Batch request completed successfully."},
        status.HTTP_207_MULTI_STATUS: {"description": "Batch request completed with partial success."},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Batch request failed."},
    },
)
async def run_batch_pipeline(
    request: BatchRequest,
    response: Response,
    batch_service: BatchService = Depends(get_batch_service),
) -> BatchPipelineResponse:
    """Run the full batch pipeline."""
    logger.info("BatchRouter batch_pipeline started | endpoint: batch/run")

    result = await batch_service.run_pipeline(executed_at=request.executed_at)
    _set_batch_response_status(response=response, batch_status=result.status)

    logger.info("BatchRouter batch_pipeline completed | endpoint: batch/run, status: %s", result.status)
    return result


@router.post(
    "/{layer}/{target}",
    response_model=BatchResponse,
    response_model_exclude_none=True,
    responses={
        status.HTTP_200_OK: {"description": "Batch request completed successfully."},
        status.HTTP_207_MULTI_STATUS: {"description": "Batch request completed with partial success."},
        status.HTTP_404_NOT_FOUND: {"description": "Batch layer/target combination is not supported."},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Batch request failed."},
    },
)
async def run_batch(
    layer: BatchLayer,
    target: BatchTarget,
    request: BatchRequest,
    response: Response,
    batch_service: BatchService = Depends(get_batch_service),
) -> BatchResponse:
    """Run a batch target for the requested layer and target."""
    logger.info("BatchRouter batch started | endpoint: batch/%s/%s", layer.value, target.value)

    # Validate the supported layer/target combination.
    if (layer, target) not in VALID_BATCH_COMBINATIONS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(f"Batch layer/target combination is not supported: layer='{layer.value}', target='{target.value}'"),
        )

    result = await batch_service.run(
        layer=layer,
        target=target,
        executed_at=request.executed_at,
    )
    _set_batch_response_status(response=response, batch_status=result.status)

    logger.info(
        "BatchRouter batch completed | endpoint: batch/%s/%s, status: %s", layer.value, target.value, result.status
    )
    return result


def _set_batch_response_status(response: Response, batch_status: str) -> None:
    """Set HTTP status code from batch execution status."""
    if batch_status == "failed":
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    elif batch_status == "partial":
        response.status_code = status.HTTP_207_MULTI_STATUS
    else:
        response.status_code = status.HTTP_200_OK
