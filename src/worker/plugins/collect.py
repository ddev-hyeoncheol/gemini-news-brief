import asyncio

from datetime import datetime, timezone

from src.core.logger import get_logger
from src.models.entities.bronze_news import BronzeNewsModel
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
                new_metadata = dict(item.metadata) if item.metadata else {}

                if isinstance(enriched, Exception):
                    logger.error("Failed to enrich url=%s: %s", item.url, enriched)
                    author = content = thumbnail_url = None
                    status_code = 500
                    error_message = f"Pipeline crash: {str(enriched)}"
                else:
                    author = enriched.get("author")
                    content = enriched.get("content")
                    thumbnail_url = enriched.get("thumbnail_url")
                    status_code = enriched.get("status_code")
                    error_message = enriched.get("error_message")

                    # Consider as failed if status is not 200 or content is missing.
                    if status_code != 200 or not content:
                        logger.warning(
                            "Enrichment missed for url=%s (status: %s, error: %s)",
                            item.url,
                            status_code,
                            error_message,
                        )

                if error_message:
                    new_metadata["error_message"] = error_message

                if status_code != 200 or not content:
                    failed_count += 1

                enriched_item = item.model_copy(
                    update={
                        "author": author,
                        "content": content,
                        "thumbnail_url": thumbnail_url,
                        "metadata": new_metadata,
                        "status_code": status_code,
                    }
                )
                enriched_items.append(enriched_item)

            # Pipeline continuity: Even if all items failed to parse (e.g., 403 block),
            # we captured the errors successfully. Return "partial" to ensure they are loaded to DB.
            status = "success" if failed_count == 0 else "partial"

            # Metric tracking: Only count items that actually successfully extracted content.
            succeeded_count = len(items) - failed_count

            logger.info(
                "[%s] Enrichment completed: %d succeeded, %d failed.",
                self.source.source,
                succeeded_count,
                failed_count,
            )

            return IngestEnrichResult(
                source=self.source.source,
                status=status,
                item_count=succeeded_count,  # Accurate funnel metric for 'enriched_count'.
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
