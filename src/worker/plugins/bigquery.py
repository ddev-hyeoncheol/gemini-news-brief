from typing import Any

from src.core.decorators import with_ingest_error_handling, with_refine_error_handling
from src.core.logger import get_logger
from src.models.entities.bronze_news import BronzeNewsModel
from src.models.entities.silver_news import SilverNewsModel
from src.models.entities.silver_news_augmented import SilverNewsAugmentedModel
from src.models.schemas.ingest import IngestLoadResult, IngestLookupResult
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
            logger.info(
                "Plugin lookup skipped | source: %s, reason: no items",
                source,
            )
            return {"items": []}

        target_items = await self.store.lookup_bronze_news(items=items)

        logger.info(
            "Plugin lookup completed | source: %s, count: %d, total: %d",
            source,
            len(target_items),
            len(items),
        )
        return {"items": target_items}

    @with_ingest_error_handling(IngestLoadResult)
    async def load(self, source: str, items: list[BronzeNewsModel]) -> dict[str, Any]:
        """Append fully enriched items into the database using the injected store."""
        if not items:
            logger.info(
                "Plugin load skipped | source: %s, reason: no items",
                source,
            )
            return {"items": []}

        await self.store.load_bronze_news(items=items)

        logger.info("Plugin load completed | source: %s, count: %d", source, len(items))
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
    async def extract_bronze_news(self, request: RefineRequest) -> dict[str, Any]:
        """Extract Bronze news items for Silver news refinement."""
        items = await self.store.extract_bronze_news(executed_at=request.executed_at)

        logger.info("Plugin extract completed | target: news, count: %d", len(items))
        return {"items": items}

    @with_refine_error_handling(RefineExtractResult)
    async def extract_silver_news(self, request: RefineRequest) -> dict[str, Any]:
        """Extract Silver news items for AI augmentation."""
        items = await self.store.extract_silver_news(executed_at=request.executed_at)

        logger.info(
            "Plugin extract completed | target: news-augmented, count: %d",
            len(items),
        )
        return {"items": items}

    @with_refine_error_handling(RefineLoadResult)
    async def load_silver_news(
        self, request: RefineRequest, items: list[SilverNewsModel]
    ) -> dict[str, Any]:
        """Load refined news items into the Silver news table."""
        if not items:
            logger.info(
                "Plugin load replacing | target: news, reason: no items"
            )

        await self.store.load_silver_news(
            executed_at=request.executed_at,
            items=items,
        )

        logger.info("Plugin load completed | target: news, count: %d", len(items))
        return {"items": items}

    @with_refine_error_handling(RefineLoadResult)
    async def load_silver_news_augmented(
        self, request: RefineRequest, items: list[SilverNewsAugmentedModel]
    ) -> dict[str, Any]:
        """Load AI-augmented news items into the Silver augmented news table."""
        if not items:
            logger.info(
                "Plugin load replacing | target: news-augmented, reason: no items"
            )

        await self.store.load_silver_news_augmented(
            executed_at=request.executed_at,
            items=items,
        )

        logger.info(
            "Plugin load completed | target: news-augmented, count: %d",
            len(items),
        )
        return {"items": items}
