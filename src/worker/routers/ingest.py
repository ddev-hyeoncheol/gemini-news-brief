from fastapi import APIRouter, Depends, HTTPException, Response, status

from src.core.logger import get_logger
from src.models.schemas.ingest import IngestRequest, IngestResponse, IngestTarget
from src.worker.services.ingest import IngestService, get_ingest_service

logger = get_logger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post(
    "/{target}",
    response_model=IngestResponse,
    responses={
        status.HTTP_200_OK: {
            "description": "Target collected and loaded successfully."
        },
        status.HTTP_207_MULTI_STATUS: {
            "model": IngestResponse,
            "description": "Partial success. Some items or sources failed.",
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "Ingestion target not found.",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": IngestResponse,
            "description": "All sources failed to ingest.",
        },
    },
)
async def ingest(
    target: str,
    request: IngestRequest,
    response: Response,
    service: IngestService = Depends(get_ingest_service),
) -> IngestResponse:
    """
    Trigger the ingestion pipeline for a supported target.

    Execute collection and loading for all registered sources in parallel.
    Adjust the HTTP response status code based on the overall pipeline success.
    """

    ingest_target = _parse_ingest_target(target)

    logger.info(
        "Router request received | endpoint: ingest, target: %s, executed_at: %s",
        ingest_target.value,
        request.executed_at.isoformat(),
    )

    result = await service.run(target=ingest_target, request=request)

    if result.status == "failed":
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    elif result.status == "partial":
        response.status_code = status.HTTP_207_MULTI_STATUS

    status_code = response.status_code or status.HTTP_200_OK
    logger.info(
        "Router response completed | endpoint: ingest, target: %s, status: %s, status_code: %d, fetched_count: %d, lookup_count: %d, enriched_count: %d, loaded_count: %d",
        ingest_target.value,
        result.status,
        status_code,
        result.fetched_count,
        result.lookup_count,
        result.enriched_count,
        result.loaded_count,
    )

    return result


def _parse_ingest_target(target: str) -> IngestTarget:
    """Return the ingestion target or raise 404 if it is not registered."""

    try:
        return IngestTarget(target)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ingestion target not found.",
        ) from exc
