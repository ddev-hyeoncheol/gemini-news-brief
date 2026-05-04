import asyncio
import json

from datetime import datetime, timezone
from google.cloud import bigquery
from typing import Any

from src.core.logger import get_logger
from src.models.entities.news import BronzeNewsModel
from src.models.schemas.ingest import IngestLookupResult, IngestLoadResult

logger = get_logger(__name__)


class BigQueryPlugin:
    """
    Plugin that handles database interactions with BigQuery (lookup and load).

    Grouped by domain: Handles all interactions with the data warehouse,
    analogous to how CollectPlugin handles external news websites.
    """

    _TABLE_ID = "bronze.news"

    def __init__(
        self, semaphore: asyncio.Semaphore, client: bigquery.Client | None
    ) -> None:
        """Initialize the BigQuery plugin with client and table config."""
        self._semaphore = semaphore
        self.client = client

    def _run_query_sync(self, query: str, job_config: bigquery.QueryJobConfig) -> Any:
        """Execute a BigQuery job synchronously (to be wrapped in to_thread)."""
        query_job = self.client.query(query, job_config=job_config)
        return query_job.result()

    async def lookup(
        self, source: str, items: list[BronzeNewsModel]
    ) -> IngestLookupResult:
        """Query BigQuery to filter out existing items and return only new or updated targets."""
        started_at = datetime.now(tz=timezone.utc)
        try:
            if not items:
                return IngestLookupResult(
                    source=source,
                    status="success",
                    started_at=started_at,
                    completed_at=datetime.now(tz=timezone.utc),
                )

            if not self.client:
                logger.info(
                    "[%s] MOCK Lookup: Returning %d items as targets.",
                    source,
                    len(items),
                )
                return IngestLookupResult(
                    source=source,
                    status="success",
                    item_count=len(items),
                    items=items,
                    started_at=started_at,
                    completed_at=datetime.now(tz=timezone.utc),
                )

            news_ids = [item.news_id for item in items]
            query = f"""
                SELECT news_id, updated_at
                FROM `{self._TABLE_ID}`
                WHERE news_id IN UNNEST(@news_ids)
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ArrayQueryParameter("news_ids", "STRING", news_ids)
                ]
            )

            async with self._semaphore:
                results = await asyncio.to_thread(
                    self._run_query_sync, query, job_config
                )

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

            logger.info(
                "[%s] Lookup completed: %d out of %d items are targets.",
                source,
                len(target_items),
                len(items),
            )

            return IngestLookupResult(
                source=source,
                status="success",
                item_count=len(target_items),
                items=target_items,
                started_at=started_at,
                completed_at=datetime.now(tz=timezone.utc),
            )
        except Exception as e:
            logger.exception("BigQuery lookup failed for source=%s", source)
            return IngestLookupResult(
                source=source,
                status="failed",
                started_at=started_at,
                completed_at=datetime.now(tz=timezone.utc),
                error_message=str(e),
            )

    async def load(self, source: str, items: list[BronzeNewsModel]) -> IngestLoadResult:
        """Upsert fully enriched items into BigQuery using a MERGE statement."""
        started_at = datetime.now(tz=timezone.utc)
        try:
            if not items:
                return IngestLoadResult(
                    source=source,
                    status="success",
                    started_at=started_at,
                    completed_at=datetime.now(tz=timezone.utc),
                )

            if not self.client:
                logger.info(
                    "[%s] MOCK Load: Successfully bypassed loading %d items.",
                    source,
                    len(items),
                )
                return IngestLoadResult(
                    source=source,
                    status="success",
                    item_count=len(items),
                    items=items,
                    started_at=started_at,
                    completed_at=datetime.now(tz=timezone.utc),
                )

            # Serialize items to a JSON string payload to pass to BigQuery safely.
            payload_str = json.dumps([item.model_dump(mode="json") for item in items])

            query = f"""
                MERGE `{self._TABLE_ID}` T
                USING (
                    SELECT
                        JSON_VALUE(item, '$.news_id') AS news_id,
                        JSON_VALUE(item, '$.source') AS source,
                        JSON_VALUE(item, '$.title') AS title,
                        JSON_VALUE(item, '$.url') AS url,
                        JSON_VALUE(item, '$.content') AS content,
                        JSON_VALUE(item, '$.author') AS author,
                        JSON_VALUE(item, '$.category') AS category,
                        JSON_VALUE(item, '$.image_url') AS image_url,
                        JSON_VALUE(item, '$.thumbnail_url') AS thumbnail_url,
                        CAST(JSON_VALUE(item, '$.published_at') AS TIMESTAMP) AS published_at,
                        CAST(JSON_VALUE(item, '$.updated_at') AS TIMESTAMP) AS updated_at,
                        CAST(JSON_VALUE(item, '$.executed_at') AS TIMESTAMP) AS executed_at,
                        PARSE_JSON(JSON_EXTRACT(item, '$.metadata')) AS metadata
                    FROM UNNEST(JSON_EXTRACT_ARRAY(@payload, '$')) AS item
                ) S
                ON T.news_id = S.news_id
                WHEN MATCHED THEN
                    UPDATE SET
                        title = S.title, url = S.url, content = S.content,
                        author = S.author, category = S.category, image_url = S.image_url,
                        thumbnail_url = S.thumbnail_url, published_at = S.published_at,
                        updated_at = S.updated_at, executed_at = S.executed_at, metadata = S.metadata
                WHEN NOT MATCHED THEN
                    INSERT (news_id, source, title, url, content, author, category, image_url, thumbnail_url, published_at, updated_at, executed_at, metadata)
                    VALUES (S.news_id, S.source, S.title, S.url, S.content, S.author, S.category, S.image_url, S.thumbnail_url, S.published_at, S.updated_at, S.executed_at, S.metadata)
            """

            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("payload", "STRING", payload_str)
                ]
            )

            async with self._semaphore:
                await asyncio.to_thread(self._run_query_sync, query, job_config)

            logger.info(
                "[%s] Load completed: %d items successfully upserted to BigQuery.",
                source,
                len(items),
            )

            return IngestLoadResult(
                source=source,
                status="success",
                item_count=len(items),
                items=items,
                started_at=started_at,
                completed_at=datetime.now(tz=timezone.utc),
            )
        except Exception as e:
            logger.exception("BigQuery load failed for source=%s", source)
            return IngestLoadResult(
                source=source,
                status="failed",
                started_at=started_at,
                completed_at=datetime.now(tz=timezone.utc),
                error_message=str(e),
            )
