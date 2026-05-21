from google.cloud import bigquery

from src.models.entities.bronze_news import BronzeNewsModel
from src.worker.plugins.stores.base import StoreBase


class BronzeStore(StoreBase):
    """
    Store class for handling Bronze tier data operations.
    Responsible for looking up existing records and loading new/updated raw news.
    """

    _BRONZE_NEWS = "bronze.news"

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

        query = f"""
            SELECT news_id, MAX(updated_at) AS updated_at
            FROM `{self._BRONZE_NEWS}`
            WHERE news_id IN UNNEST(@news_ids)
            GROUP BY news_id
        """
        results = await self.execute_query(query, job_config)

        existing_data = {row.news_id: row.updated_at for row in results}
        target_items = []
        for item in items:
            if item.news_id not in existing_data:
                target_items.append(item)
                continue

            existing_updated_at = existing_data[item.news_id]
            if existing_updated_at is None:
                if item.updated_at is not None:
                    target_items.append(item)
                continue

            if (item.updated_at or item.published_at) > existing_updated_at:
                target_items.append(item)

        return target_items

    async def load_bronze_news(self, items: list[BronzeNewsModel]) -> None:
        """Append fully enriched news items into BigQuery using a JSON load job."""
        await self.load_models(table_id=self._BRONZE_NEWS, items=items)
