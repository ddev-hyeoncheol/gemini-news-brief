from fastapi import APIRouter, Depends

from src.core.logger import get_logger
from src.models.schemas.ingest import IngestRequest, IngestResponse
from src.worker.services.ingest import IngestService, get_ingest_service

logger = get_logger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("", response_model=IngestResponse)
async def ingest(
    request: IngestRequest,
    service: IngestService = Depends(get_ingest_service),
) -> IngestResponse:
    logger.info(
        "Ingest triggered | executed_at=%s window=%dm",
        request.scheduled_at.isoformat(),
        request.window,
    )
    return await service.run(request)
