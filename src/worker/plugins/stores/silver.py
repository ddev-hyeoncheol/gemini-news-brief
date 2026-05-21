from datetime import datetime

from src.models.entities.bronze_news import BronzeNewsModel
from src.models.entities.silver_news import SilverNewsModel
from src.models.entities.silver_news_augmented import SilverNewsAugmentedModel
from src.worker.plugins.stores.base import StoreBase


class SilverStore(StoreBase):
    """
    Store Silver-tier extraction and load operations.
    Encapsulate physical table access for Silver refinement pipelines.
    """

    _BRONZE_NEWS = "bronze.news"
    _SILVER_NEWS = "silver.news"
    _SILVER_NEWS_AUGMENTED = "silver.news_augmented"

    async def extract_bronze_news(self, executed_at: datetime) -> list[BronzeNewsModel]:
        """Extract Bronze news for a batch execution time."""
        return await self.extract_models(
            table_id=self._BRONZE_NEWS,
            model_class=BronzeNewsModel,
            filters={"executed_at": executed_at},
        )

    async def extract_silver_news(self, executed_at: datetime) -> list[SilverNewsModel]:
        """Extract Silver news for a batch execution time."""
        return await self.extract_models(
            table_id=self._SILVER_NEWS,
            model_class=SilverNewsModel,
            filters={"executed_at": executed_at},
        )

    async def load_silver_news(
        self, executed_at: datetime, items: list[SilverNewsModel]
    ) -> None:
        """Delete existing batch data and load transformed Silver news."""
        filters = {"executed_at": executed_at}
        await self.delete_models(table_id=self._SILVER_NEWS, filters=filters)
        await self.load_models(table_id=self._SILVER_NEWS, items=items)

    async def load_silver_news_augmented(
        self, executed_at: datetime, items: list[SilverNewsAugmentedModel]
    ) -> None:
        """Delete existing batch data and load AI-augmented Silver news."""
        filters = {"executed_at": executed_at}
        await self.delete_models(
            table_id=self._SILVER_NEWS_AUGMENTED,
            filters=filters,
        )
        await self.load_models(table_id=self._SILVER_NEWS_AUGMENTED, items=items)
