from fastapi import APIRouter, Depends, Response, status

from src.core.logger import get_logger
from src.models.schemas.ingest import IngestRequest, IngestResponse
from src.worker.services.ingest import IngestService, get_ingest_service

logger = get_logger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post(
    "",
    response_model=IngestResponse,
    responses={
        status.HTTP_200_OK: {
            "description": "All sources collected and loaded successfully."
        },
        status.HTTP_207_MULTI_STATUS: {
            "model": IngestResponse,
            "description": "Partial success. Some items or sources failed.",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": IngestResponse,
            "description": "All sources failed to ingest.",
        },
    },
)
async def ingest(
    request: IngestRequest,
    response: Response,
    service: IngestService = Depends(get_ingest_service),
) -> IngestResponse:
    """
    Trigger the news ingestion pipeline.

    Execute collection and loading for all registered sources in parallel.
    Adjust the HTTP response status code based on the overall pipeline success.
    """
    logger.info("Ingest triggered | executed_at: %s", request.executed_at.isoformat())

    result = await service.run(request)

    if result.status == "failed":
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    elif result.status == "partial":
        response.status_code = status.HTTP_207_MULTI_STATUS

    logger.info(
        "Ingest completed | status: %s, fetched: %d, lookup: %d, enriched: %d, loaded: %d",
        result.status,
        result.fetched_count,
        result.lookup_count,
        result.enriched_count,
        result.loaded_count,
    )

    return result
