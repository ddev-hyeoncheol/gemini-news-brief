from datetime import timezone
from google.cloud import bigquery

from src.core.logger import get_logger
from src.models.entities.bronze_news import BronzeNewsModel
from src.worker.plugins.stores.base import StoreBase

logger = get_logger(__name__)


class BronzeStore(StoreBase):
    """
    Store class for handling Bronze tier data operations.
    Responsible for looking up existing records and loading new/updated raw news.
    """

    _BRONZE_NEWS = "bronze.news"

    _LOOKUP_BRONZE_NEWS_QUERY_TEMPLATE = """
        SELECT news_id, MAX(updated_at) AS updated_at
        FROM `{table_id}`
        WHERE news_id IN UNNEST(@news_ids)
        GROUP BY news_id
    """

    async def lookup_bronze_news(
        self, items: list[BronzeNewsModel]
    ) -> list[BronzeNewsModel]:
        """Query BigQuery to filter out existing news items and return only new or updated targets."""
        if not items:
            return []

        news_ids = [item.news_id for item in items]
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ArrayQueryParameter("news_ids", "STRING", news_ids)
            ]
        )

        query = self._LOOKUP_BRONZE_NEWS_QUERY_TEMPLATE.format(
            table_id=self._BRONZE_NEWS
        )
        # execute_query inherits from StoreBase, applying semaphore automatically.
        results = await self.execute_query(query, job_config)

        existing_data = {row.news_id: row.updated_at for row in results}
        target_items = []

        for item in items:
            existing_updated_at = existing_data.get(item.news_id)
            if existing_updated_at:
                # Ensure existing_updated_at is timezone-aware (UTC).
                if existing_updated_at.tzinfo is None:
                    existing_updated_at = existing_updated_at.replace(
                        tzinfo=timezone.utc
                    )
                # Skip if the existing record in DB is newer or the same as the feed item.
                item_updated_at = item.updated_at or item.published_at
                if item_updated_at <= existing_updated_at:
                    continue
            target_items.append(item)

        return target_items

    async def load_bronze_news(self, items: list[BronzeNewsModel]) -> None:
        """Append fully enriched news items into BigQuery using a JSON load job."""
        if not items:
            return

        json_rows = [item.model_dump(mode="json") for item in items]
        await self.execute_load_json(json_rows, destination=self._BRONZE_NEWS)
