from datetime import datetime
from typing import Literal

from google.cloud import bigquery

from src.models.entities.bronze_news import BronzeNewsModel
from src.providers.bigquery import BigQueryProvider


class BronzeStore:
    """
    Store Bronze-tier extract, lookup, and load operations.
    Encapsulate physical table access for Bronze collection pipelines.
    """

    _BRONZE_NEWS = "bronze.news"

    def __init__(self, provider: BigQueryProvider) -> None:
        """Initialize the store with BigQuery provider."""
        self._provider = provider

    async def extract_bronze_news(self, executed_at: datetime) -> list[BronzeNewsModel]:
        """Extract Bronze news for a batch execution time."""
        query = f"SELECT * FROM `{self._BRONZE_NEWS}` WHERE executed_at = @executed_at"
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("executed_at", "TIMESTAMP", executed_at)]
        )
        results = await self._provider.execute_query(query, job_config)
        return [BronzeNewsModel(**dict(row)) for row in results]

    async def lookup_bronze_news(
        self,
        executed_at: datetime,
        items: list[BronzeNewsModel],
        lookup_key: Literal["entry_id", "news_id"],
    ) -> list[BronzeNewsModel]:
        """Return Bronze news items not already stored as successful records."""
        if not items:
            return []

        lookup_values = [getattr(item, lookup_key) for item in items]
        query = f"""
            SELECT
                {lookup_key}, status AS latest_status
            FROM (
                SELECT
                    {lookup_key}, status,
                    ROW_NUMBER() OVER (PARTITION BY {lookup_key} ORDER BY executed_at DESC) AS rn
                FROM `{self._BRONZE_NEWS}`
                WHERE executed_at >= TIMESTAMP_SUB(@executed_at, INTERVAL 7 DAY)
                    AND {lookup_key} IN UNNEST(@lookup_values)
            )
            WHERE rn = 1
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("executed_at", "TIMESTAMP", executed_at),
                bigquery.ArrayQueryParameter("lookup_values", "STRING", lookup_values),
            ]
        )

        results = await self._provider.execute_query(query, job_config)
        existing_status = {getattr(row, lookup_key): row.latest_status for row in results}
        target_items = []
        for item in items:
            item_lookup_value = getattr(item, lookup_key)
            # Retry items whose latest stored attempt failed.
            if item_lookup_value not in existing_status or existing_status[item_lookup_value] == "failed":
                target_items.append(item)

        return target_items

    async def load_bronze_news(self, items: list[BronzeNewsModel]) -> None:
        """Append Bronze news into BigQuery using a JSON load job."""
        json_rows = [item.model_dump(mode="json") for item in items]
        await self._provider.execute_load_json(json_rows=json_rows, table_id=self._BRONZE_NEWS)
