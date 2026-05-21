from fastapi import APIRouter, Depends, HTTPException, Response, status

from src.core.logger import get_logger
from src.models.schemas.refine import RefineRequest, RefineResponse, RefineTarget
from src.worker.services.refine import RefineService, get_refine_service

logger = get_logger(__name__)

router = APIRouter(prefix="/refine", tags=["refine"])


@router.post(
    "/{target}",
    response_model=RefineResponse,
    responses={
        status.HTTP_200_OK: {"description": "Target refined and loaded successfully."},
        status.HTTP_207_MULTI_STATUS: {
            "model": RefineResponse,
            "description": "Partial success. Some items failed during transformation or load.",
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "Refinement target not found.",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": RefineResponse,
            "description": "Pipeline failed to refine the target.",
        },
    },
)
async def refine(
    target: str,
    request: RefineRequest,
    response: Response,
    service: RefineService = Depends(get_refine_service),
) -> RefineResponse:
    """
    Trigger the refinement pipeline for a supported target.

    Execute extraction, transformation, and loading sequentially.
    Adjust the HTTP response status code based on the overall pipeline success.
    """

    refine_target = _parse_refine_target(target)

    logger.info(
        "Router request received | endpoint: refine, target: %s, executed_at: %s",
        refine_target.value,
        request.executed_at.isoformat(),
    )

    result = await service.run(target=refine_target, request=request)

    if result.status == "failed":
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    elif result.status == "partial":
        response.status_code = status.HTTP_207_MULTI_STATUS

    status_code = response.status_code or status.HTTP_200_OK
    logger.info(
        "Router response completed | endpoint: refine, target: %s, status: %s, status_code: %d, extracted_count: %d, transformed_count: %d, loaded_count: %d",
        refine_target.value,
        result.status,
        status_code,
        result.extracted_count,
        result.transformed_count,
        result.loaded_count,
    )

    return result


def _parse_refine_target(target: str) -> RefineTarget:
    """Return the refinement target or raise 404 if it is not registered."""

    try:
        return RefineTarget(target)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refinement target not found.",
        ) from exc
