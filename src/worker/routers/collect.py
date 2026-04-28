from fastapi import APIRouter, Depends

from src.core.logger import get_logger
from src.models.schemas.collect import CollectRequest, CollectResponse
from src.worker.services.collect import CollectService, get_collect_service

logger = get_logger(__name__)

router = APIRouter(prefix="/collect", tags=["collect"])


@router.post("", response_model=CollectResponse)
async def collect(
    request: CollectRequest,
    service: CollectService = Depends(get_collect_service),
) -> CollectResponse:
    logger.info(
        "Collection triggered | executed_at=%s window=%dm",
        request.scheduled_at.isoformat(),
        request.window,
    )
    return await service.run(request)
