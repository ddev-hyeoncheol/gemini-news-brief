import asyncio
from datetime import datetime, timezone
from typing import Any

from src.core.logger import get_logger
from src.models.entities.news import BronzeNewsModel
from src.models.schemas.ingest import IngestLoadResult
from src.worker.plugins.base import BasePlugin

logger = get_logger(__name__)


class BigQueryPlugin(BasePlugin):
    """Dummy plugin that bypasses actual BigQuery insertion for development."""

    def __init__(self, semaphore: asyncio.Semaphore, *args: Any, **kwargs: Any) -> None:
        """Initialize the dummy BigQuery plugin with a concurrency semaphore."""
        self._semaphore = semaphore

    async def execute(
        self, source: str, items: list[BronzeNewsModel]
    ) -> IngestLoadResult:
        """Simulate the insertion of items into BigQuery and return an IngestLoadResult."""
        started_at = datetime.now(tz=timezone.utc)
        try:
            if not items:
                return IngestLoadResult(
                    source=source,
                    status="success",
                    started_at=started_at,
                    loaded_at=datetime.now(tz=timezone.utc),
                )

            async with self._semaphore:
                logger.info(
                    "[MOCK] Simulated inserting %d items into BigQuery.", len(items)
                )
                await asyncio.sleep(0.5)  # Simulate network delay

            return IngestLoadResult(
                source=source,
                status="success",
                target_count=len(items),
                loaded_count=len(items),
                started_at=started_at,
                loaded_at=datetime.now(tz=timezone.utc),
            )
        except Exception as e:
            logger.exception("BigQuery mock load failed for source=%s", source)
            return IngestLoadResult(
                source=source,
                status="failed",
                target_count=len(items),
                started_at=started_at,
                loaded_at=datetime.now(tz=timezone.utc),
                error_message=str(e),
            )
