from fastapi import APIRouter, Depends, Response, status

from src.core.logger import get_logger
from src.models.schemas.ingest import IngestRequest, IngestResponse
from src.worker.services.ingest import IngestService, get_ingest_service

logger = get_logger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post(
    "/run",
    response_model=IngestResponse,
    response_model_exclude_none=True,
    responses={
        status.HTTP_200_OK: {"description": "Ingest request completed successfully."},
        status.HTTP_207_MULTI_STATUS: {"description": "Ingest request completed with partial success."},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Ingest request failed."},
    },
)
async def run_ingest(
    request: IngestRequest,
    response: Response,
    ingest_service: IngestService = Depends(get_ingest_service),
) -> IngestResponse:
    """Run the news ingestion batch."""
    logger.info("IngestRouter ingest started | endpoint: ingest/run")

    result = await ingest_service.run(executed_at=request.executed_at)

    # Map execution status to the HTTP status code.
    if result.status == "failed":
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    elif result.status == "partial":
        response.status_code = status.HTTP_207_MULTI_STATUS
    else:
        response.status_code = status.HTTP_200_OK

    logger.info("IngestRouter ingest completed | endpoint: ingest/run, status: %s", result.status)
    return result
