import asyncio
from datetime import datetime, timezone

from src.core.logger import get_logger
from src.models.entities.news import BronzeNewsModel
from src.models.schemas.ingest import IngestLookupResult, IngestLoadResult

logger = get_logger(__name__)


class BigQueryPlugin:
    """Dummy plugin that bypasses actual BigQuery operations for local development."""

    def __init__(self, semaphore: asyncio.Semaphore) -> None:
        """Initialize the dummy BigQuery plugin with a concurrency semaphore."""
        self._semaphore = semaphore

    async def lookup(
        self, source: str, items: list[BronzeNewsModel]
    ) -> IngestLookupResult:
        """Simulate DB lookup by returning all input items as targets."""
        started_at = datetime.now(tz=timezone.utc)
        try:
            if not items:
                return IngestLookupResult(
                    source=source,
                    status="success",
                    started_at=started_at,
                    completed_at=datetime.now(tz=timezone.utc),
                )

            async with self._semaphore:
                logger.info(
                    "[MOCK] Simulated lookup for %d items in BigQuery.", len(items)
                )
                await asyncio.sleep(0.1)  # Simulate network delay.

            return IngestLookupResult(
                source=source,
                status="success",
                item_count=len(items),
                items=items,
                started_at=started_at,
                completed_at=datetime.now(tz=timezone.utc),
            )
        except Exception as e:
            logger.exception("BigQuery mock lookup failed for source=%s", source)
            return IngestLookupResult(
                source=source,
                status="failed",
                started_at=started_at,
                completed_at=datetime.now(tz=timezone.utc),
                error_message=str(e),
            )

    async def load(self, source: str, items: list[BronzeNewsModel]) -> IngestLoadResult:
        """Simulate the insertion and merge of items into BigQuery."""
        started_at = datetime.now(tz=timezone.utc)
        try:
            if not items:
                return IngestLoadResult(
                    source=source,
                    status="success",
                    started_at=started_at,
                    completed_at=datetime.now(tz=timezone.utc),
                )

            async with self._semaphore:
                logger.info(
                    "[MOCK] Simulated loading %d items into BigQuery.", len(items)
                )
                await asyncio.sleep(0.5)  # Simulate network delay.

            return IngestLoadResult(
                source=source,
                status="success",
                item_count=len(items),
                items=items,
                started_at=started_at,
                completed_at=datetime.now(tz=timezone.utc),
            )
        except Exception as e:
            logger.exception("BigQuery mock load failed for source=%s", source)
            return IngestLoadResult(
                source=source,
                status="failed",
                started_at=started_at,
                completed_at=datetime.now(tz=timezone.utc),
                error_message=str(e),
            )
