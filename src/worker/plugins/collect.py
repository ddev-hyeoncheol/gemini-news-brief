import asyncio
from typing import Any

from src.core.decorators import with_ingest_error_handling
from src.core.logger import get_logger
from src.models.entities.bronze_news import BronzeNewsModel
from src.models.schemas.ingest import (
    IngestEnrichResult,
    IngestFetchResult,
    IngestRequest,
)
from src.worker.plugins.sources.base import SourceBase

logger = get_logger(__name__)


class CollectPlugin:
    """
    Plugin that orchestrates external news collection (fetch and enrich) using an injected Source.

    Grouped by domain: Handles all interactions with external news websites,
    analogous to how IngestDbPlugin handles database interactions.
    """

    def __init__(self, source: SourceBase) -> None:
        """Initialize the collection plugin with a specific news source."""
        self._source = source

    @property
    def source(self) -> str:
        """Return the unique identifier of the injected source."""
        return self._source.source

    @with_ingest_error_handling(IngestFetchResult)
    async def fetch(self, request: IngestRequest) -> dict[str, Any]:
        """Fetch raw RSS items from the source."""
        items = await self._source.fetch(request)

        logger.info(
            "Plugin fetch completed | source: %s, count: %d",
            self.source,
            len(items),
        )
        return {"items": items}

    @with_ingest_error_handling(IngestEnrichResult)
    async def enrich(self, items: list[BronzeNewsModel]) -> dict[str, Any]:
        """Enrich targeted items with full article content using the source's scraper."""
        if not items:
            logger.info(
                "Plugin enrich skipped | source: %s, reason: no items",
                self.source,
            )
            return {}

        tasks = [self._source.enrich(item.url) for item in items]
        enrichments = await asyncio.gather(*tasks, return_exceptions=True)

        enriched_items = []
        failed_count = 0

        for item, enriched in zip(items, enrichments):
            new_metadata = dict(item.metadata) if item.metadata else {}

            if isinstance(enriched, Exception):
                logger.warning(
                    "Plugin enrich item failed | source: %s, url: %s, reason: exception, error: %s",
                    self.source,
                    item.url,
                    enriched,
                )
                author = content = thumbnail_url = None
                status_code = 500
                error_message = f"Pipeline crash::{type(enriched).__name__}::{enriched}"
            else:
                author = enriched.get("author")
                content = enriched.get("content")
                thumbnail_url = enriched.get("thumbnail_url")
                status_code = enriched.get("status_code")
                error_message = enriched.get("error_message")

                if status_code != 200 or not content:
                    if not error_message:
                        if status_code != 200:
                            error_message = (
                                f"HTTP status not OK::status_code={status_code}"
                            )
                        else:
                            error_message = "Content unavailable::empty content"

                    logger.warning(
                        "Plugin enrich item failed | source: %s, url: %s, reason: content unavailable, status_code: %s, error: %s",
                        self.source,
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

        # Metric tracking: Count records with successfully extracted article content.
        succeeded_count = len(items) - failed_count

        logger.info(
            "Plugin enrich completed | source: %s, count: %d, failed_count: %d",
            self.source,
            succeeded_count,
            failed_count,
        )

        return {
            "status": status,
            "item_count": succeeded_count,
            "items": enriched_items,
        }
