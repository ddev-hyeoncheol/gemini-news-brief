from fastapi import APIRouter, Depends, Response, status

from src.core.logger import get_logger
from src.models.schemas.refine import RefineRequest, RefineResponse
from src.worker.services.refine import RefineService, get_refine_service

logger = get_logger(__name__)

router = APIRouter(prefix="/refine", tags=["refine"])


@router.post(
    "",
    response_model=RefineResponse,
    responses={
        status.HTTP_200_OK: {
            "description": "Target table refined and loaded successfully."
        },
        status.HTTP_207_MULTI_STATUS: {
            "model": RefineResponse,
            "description": "Partial success. Some items failed during transformation or load.",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": RefineResponse,
            "description": "Pipeline failed to refine the target table.",
        },
    },
)
async def refine(
    request: RefineRequest,
    response: Response,
    service: RefineService = Depends(get_refine_service),
) -> RefineResponse:
    """
    Trigger the refinement pipeline for a specific target table.

    Execute extraction, transformation, and loading sequentially.
    Adjust the HTTP response status code based on the overall pipeline success.
    """
    logger.info(
        "Refine triggered | target: %s, executed_at: %s",
        request.target_table,
        request.executed_at.isoformat(),
    )

    result = await service.run(request)

    if result.status == "failed":
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    elif result.status == "partial":
        response.status_code = status.HTTP_207_MULTI_STATUS

    logger.info(
        "Refine completed | target: %s, status: %s, extracted: %d, transformed: %d, loaded: %d",
        result.target_table,
        result.status,
        result.extracted_count,
        result.transformed_count,
        result.loaded_count,
    )

    return result
