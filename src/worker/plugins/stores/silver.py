from datetime import datetime

from google.cloud import bigquery

from src.models.entities.silver_news import SilverNewsModel
from src.models.entities.silver_news_augmented import SilverNewsAugmentedModel
from src.providers.bigquery import BigQueryProvider


class SilverStore:
    """
    Store Silver-tier extract and load operations.
    Encapsulate physical table access for Silver refinement pipelines.
    """

    _SILVER_NEWS = "silver.news"
    _SILVER_NEWS_AUGMENTED = "silver.news_augmented"

    def __init__(self, provider: BigQueryProvider) -> None:
        """Initialize the store with BigQuery provider."""
        self._provider = provider

    async def extract_silver_news(self, executed_at: datetime) -> list[SilverNewsModel]:
        """Extract Silver news for a batch execution time."""
        query = f"SELECT * FROM `{self._SILVER_NEWS}` WHERE executed_at = @executed_at"
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("executed_at", "TIMESTAMP", executed_at)]
        )
        results = await self._provider.execute_query(query, job_config)
        return [SilverNewsModel(**dict(row)) for row in results]

    async def load_silver_news(self, executed_at: datetime, items: list[SilverNewsModel]) -> None:
        """Replace Silver news for a batch execution time."""
        delete_query = f"DELETE FROM `{self._SILVER_NEWS}` WHERE executed_at = @executed_at"
        delete_job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("executed_at", "TIMESTAMP", executed_at)]
        )
        await self._provider.execute_query(delete_query, delete_job_config)

        json_rows = [item.model_dump(mode="json") for item in items]
        await self._provider.execute_load_json(json_rows=json_rows, table_id=self._SILVER_NEWS)

    async def load_silver_news_augmented(self, executed_at: datetime, items: list[SilverNewsAugmentedModel]) -> None:
        """Replace AI-augmented Silver news for a batch execution time."""
        delete_query = f"DELETE FROM `{self._SILVER_NEWS_AUGMENTED}` WHERE executed_at = @executed_at"
        delete_job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("executed_at", "TIMESTAMP", executed_at)]
        )
        await self._provider.execute_query(delete_query, delete_job_config)

        json_rows = [item.model_dump(mode="json") for item in items]
        await self._provider.execute_load_json(json_rows=json_rows, table_id=self._SILVER_NEWS_AUGMENTED)
