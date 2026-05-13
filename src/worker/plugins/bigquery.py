from typing import Any

from src.core.logger import get_logger
from src.core.decorators import with_ingest_error_handling, with_refine_error_handling
from src.models.entities.bronze_news import BronzeNewsModel
from src.models.schemas.ingest import IngestLookupResult, IngestLoadResult
from src.models.schemas.refine import (
    RefineExtractResult,
    RefineLoadResult,
    RefineRequest,
)
from src.worker.plugins.stores.bronze import BronzeStore
from src.worker.plugins.stores.silver import SilverStore

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


class RefineDbPlugin:
    """
    Plugin that orchestrates database interactions for the refinement pipeline.
    Wraps the domain-specific SilverStore to handle errors and format DTO results.
    """

    def __init__(self, store: SilverStore) -> None:
        """Initialize the DB plugin with an injected SilverStore."""
        self.store = store

    @with_refine_error_handling(RefineExtractResult)
    async def extract(self, request: RefineRequest) -> dict[str, Any]:
        """Extract raw items from the Bronze tier for transformation."""
        if request.target_table == self.store._SILVER_NEWS:
            items = await self.store.extract_bronze_news(request.executed_at)
        else:
            # For future expansion (e.g. extracting Silver data for Augmented tier)
            items = []

        logger.info(
            "[%s] Extract completed | count: %d", request.target_table, len(items)
        )
        return {"items": items}

    @with_refine_error_handling(RefineLoadResult)
    async def load(self, request: RefineRequest, items: list[Any]) -> dict[str, Any]:
        """Load transformed items into the corresponding Silver tier table."""
        if not items:
            logger.info("[%s] Load skipped | reason: no items", request.target_table)
            return {"items": []}

        if request.target_table == self.store._SILVER_NEWS:
            await self.store.load_silver_news(request.executed_at, items)
        elif request.target_table == self.store._SILVER_NEWS_AUGMENTED:
            await self.store.load_augmented_news(request.executed_at, items)

        logger.info("[%s] Load completed | count: %d", request.target_table, len(items))
        return {"items": items}
