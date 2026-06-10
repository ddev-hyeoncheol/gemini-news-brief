from datetime import datetime
from typing import Literal

from src.core.logger import get_logger
from src.models.entities.bronze_news import BronzeNewsModel
from src.models.entities.silver_news import SilverNewsModel
from src.models.entities.silver_news_augmented import SilverNewsAugmentedModel
from src.worker.plugins.stores.bronze import BronzeStore
from src.worker.plugins.stores.silver import SilverStore

logger = get_logger(__name__)


class DbPlugin:
    """
    Plugin that orchestrates database phase operations.
    Delegates physical BigQuery operations to BronzeStore and SilverStore.
    """

    def __init__(self, bronze_store: BronzeStore, silver_store: SilverStore) -> None:
        """Initialize the DB plugin with injected stores."""
        self._bronze_store = bronze_store
        self._silver_store = silver_store

    async def run_extract_bronze_news(self, executed_at: datetime) -> list[BronzeNewsModel]:
        """Extract Bronze news items for Silver news refinement."""
        items = await self._bronze_store.extract_bronze_news(executed_at=executed_at)

        logger.info("DbPlugin extract_bronze_news completed | count: %d", len(items))
        return items

    async def run_lookup_bronze_news(
        self,
        executed_at: datetime,
        source: str,
        items: list[BronzeNewsModel],
        lookup_key: Literal["entry_id", "news_id"],
    ) -> list[BronzeNewsModel]:
        """Return Bronze news items that still need database load."""
        if not items:
            logger.info(
                "DbPlugin lookup_bronze_news skipped | source: %s, lookup_key: %s, reason: no items",
                source,
                lookup_key,
            )
            return []

        target_items = await self._bronze_store.lookup_bronze_news(
            executed_at=executed_at,
            items=items,
            lookup_key=lookup_key,
        )

        logger.info(
            "DbPlugin lookup_bronze_news completed | source: %s, lookup_key: %s, count: %d",
            source,
            lookup_key,
            len(target_items),
        )
        return target_items

    async def run_load_bronze_news(
        self,
        source: str,
        items: list[BronzeNewsModel],
    ) -> None:
        """Append Bronze news items using the bronze store."""
        if not items:
            logger.info("DbPlugin load_bronze_news skipped | source: %s, reason: no items", source)
            return

        await self._bronze_store.load_bronze_news(items=items)

        logger.info("DbPlugin load_bronze_news completed | source: %s, count: %d", source, len(items))

    async def run_extract_silver_news(self, executed_at: datetime) -> list[SilverNewsModel]:
        """Extract Silver news items for AI augmentation."""
        items = await self._silver_store.extract_silver_news(executed_at=executed_at)

        logger.info("DbPlugin extract_silver_news completed | count: %d", len(items))
        return items

    async def run_load_silver_news(
        self,
        executed_at: datetime,
        items: list[SilverNewsModel],
    ) -> None:
        """Replace Silver news for a batch execution time."""
        await self._silver_store.load_silver_news(executed_at=executed_at, items=items)

        logger.info("DbPlugin load_silver_news completed | count: %d", len(items))

    async def run_load_silver_news_augmented(
        self,
        executed_at: datetime,
        items: list[SilverNewsAugmentedModel],
    ) -> None:
        """Replace AI-augmented Silver news for a batch execution time."""
        await self._silver_store.load_silver_news_augmented(executed_at=executed_at, items=items)

        logger.info("DbPlugin load_silver_news_augmented completed | count: %d", len(items))
