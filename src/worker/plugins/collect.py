import asyncio

from datetime import datetime, timezone

from src.core.logger import get_logger
from src.models.entities.news import BronzeNewsModel
from src.models.schemas.ingest import (
    IngestRequest,
    IngestFetchResult,
    IngestEnrichResult,
)
from src.worker.plugins.sources.base import SourceBase

logger = get_logger(__name__)


class CollectPlugin:
    """
    Plugin that orchestrates external news collection (fetch and enrich) using an injected Source.

    Grouped by domain: Handles all interactions with external news websites,
    analogous to how BigQueryPlugin handles database interactions.
    """

    def __init__(self, source: SourceBase) -> None:
        """Initialize the collection plugin with a specific news source."""
        self.source = source

    async def fetch(self, request: IngestRequest) -> IngestFetchResult:
        """Fetch raw RSS items from the source."""
        started_at = datetime.now(tz=timezone.utc)
        try:
            items = await self.source.fetch(request)

            logger.info(
                "[%s] Fetched %d items from RSS feed.",
                self.source.source,
                len(items),
            )
            return IngestFetchResult(
                source=self.source.source,
                status="success",
                item_count=len(items),
                items=items,
                started_at=started_at,
                completed_at=datetime.now(tz=timezone.utc),
            )
        except Exception as e:
            logger.exception("Fetch failed for source=%s", self.source.source)
            return IngestFetchResult(
                source=self.source.source,
                status="failed",
                started_at=started_at,
                completed_at=datetime.now(tz=timezone.utc),
                error_message=str(e),
            )

    async def enrich(self, items: list[BronzeNewsModel]) -> IngestEnrichResult:
        """Enrich targeted items with full article content using the source's scraper."""
        started_at = datetime.now(tz=timezone.utc)
        if not items:
            return IngestEnrichResult(
                source=self.source.source,
                status="success",
                started_at=started_at,
                completed_at=datetime.now(tz=timezone.utc),
            )

        try:
            tasks = [self.source.enrich(item.url) for item in items]
            enrichments = await asyncio.gather(*tasks, return_exceptions=True)

            enriched_items = []
            failed_count = 0

            for item, enriched in zip(items, enrichments):
                if isinstance(enriched, Exception):
                    logger.error("Failed to enrich url=%s: %s", item.url, enriched)
                    failed_count += 1
                    continue

                enriched_item = item.model_copy(
                    update={
                        "content": enriched.get("content"),
                        "author": enriched.get("author"),
                        "thumbnail_url": enriched.get("thumbnail_url"),
                    }
                )
                enriched_items.append(enriched_item)

            status = "success"
            if failed_count == len(items):
                status = "failed"
            elif failed_count > 0:
                status = "partial"

            return IngestEnrichResult(
                source=self.source.source,
                status=status,
                item_count=len(enriched_items),
                items=enriched_items,
                started_at=started_at,
                completed_at=datetime.now(tz=timezone.utc),
            )
        except Exception as e:
            logger.exception("Enrichment failed for source=%s", self.source.source)
            return IngestEnrichResult(
                source=self.source.source,
                status="failed",
                started_at=started_at,
                completed_at=datetime.now(tz=timezone.utc),
                error_message=str(e),
            )
