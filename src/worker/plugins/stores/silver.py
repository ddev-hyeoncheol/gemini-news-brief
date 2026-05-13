from datetime import datetime

from google.cloud import bigquery

from src.core.logger import get_logger
from src.models.entities.bronze_news import BronzeNewsModel
from src.models.entities.silver_news import SilverNewsModel
from src.models.entities.silver_news_augmented import SilverNewsAugmentedModel
from src.worker.plugins.stores.base import StoreBase

logger = get_logger(__name__)


class SilverStore(StoreBase):
    """
    Store class for handling Silver tier data operations using a strict ETL pattern.
    Responsible for fetching Bronze data into Python memory, and loading transformed Silver data.
    """

    _BRONZE_NEWS = "bronze.news"
    _SILVER_NEWS = "silver.news"
    _SILVER_NEWS_AUGMENTED = "silver.news_augmented"

    _EXTRACT_BRONZE_NEWS_QUERY_TEMPLATE = """
        SELECT *
        FROM `{table_id}`
        WHERE executed_at = @executed_at
    """

    async def extract_bronze_news(self, executed_at: datetime) -> list[BronzeNewsModel]:
        """
        Extract raw news from the Bronze tier for a specific batch execution time.
        Bring data into Python memory for transformation.
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("executed_at", "TIMESTAMP", executed_at)
            ]
        )

        query = self._EXTRACT_BRONZE_NEWS_QUERY_TEMPLATE.format(
            table_id=self._BRONZE_NEWS
        )
        results = await self.execute_query(query, job_config)

        # Map BigQuery RowIterator to Pydantic models
        return [BronzeNewsModel(**dict(row)) for row in results]

    async def load_silver_news(
        self, executed_at: datetime, items: list[SilverNewsModel]
    ) -> None:
        """
        Delete existing batch data for idempotency and load transformed news into the Silver tier.
        """
        await self.execute_delete_batch(self._SILVER_NEWS, executed_at)

        json_rows = [item.model_dump(mode="json") for item in items]
        await self.execute_load_json(json_rows, table_id=self._SILVER_NEWS)

    async def load_augmented_news(
        self, executed_at: datetime, items: list[SilverNewsAugmentedModel]
    ) -> None:
        """
        Delete existing batch data for idempotency and load AI-augmented news into the Silver tier.
        """
        await self.execute_delete_batch(self._SILVER_NEWS_AUGMENTED, executed_at)

        json_rows = [item.model_dump(mode="json") for item in items]
        await self.execute_load_json(json_rows, table_id=self._SILVER_NEWS_AUGMENTED)
