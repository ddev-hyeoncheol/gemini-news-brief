from typing import Any

from src.core.logger import get_logger
from src.core.decorators import with_ingest_error_handling
from src.models.entities.bronze_news import BronzeNewsModel
from src.models.schemas.ingest import IngestLookupResult, IngestLoadResult
from src.worker.plugins.stores.bronze import BronzeStore

logger = get_logger(__name__)


class IngestDbPlugin:
    """
    Plugin that orchestrates database interactions for the ingestion pipeline.
    Wraps the domain-specific BronzeStore to handle errors and format DTO results.
    """

    def __init__(self, store: BronzeStore) -> None:
        """Initialize the DB plugin with an injected BronzeStore."""
        self.store = store

    @with_ingest_error_handling(IngestLookupResult)
    async def lookup(self, source: str, items: list[BronzeNewsModel]) -> dict[str, Any]:
        """Filter out existing items using the injected store."""
        if not items:
            logger.info("[%s] Lookup skipped | reason: no items", source)
            return {"items": []}

        target_items = await self.store.lookup_bronze_news(items)

        logger.info(
            "[%s] Lookup completed | targets: %d, total: %d",
            source,
            len(target_items),
            len(items),
        )
        return {"items": target_items}

    @with_ingest_error_handling(IngestLoadResult)
    async def load(self, source: str, items: list[BronzeNewsModel]) -> dict[str, Any]:
        """Append fully enriched items into the database using the injected store."""
        if not items:
            logger.info("[%s] Load skipped | reason: no items", source)
            return {"items": []}

        await self.store.load_bronze_news(items)

        logger.info("[%s] Load completed | count: %d", source, len(items))
        return {"items": items}
