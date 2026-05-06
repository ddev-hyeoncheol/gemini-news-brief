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
        self._client = client

    def _run_query_sync(self, query: str, job_config: bigquery.QueryJobConfig) -> Any:
        """Execute a BigQuery job synchronously (to be wrapped in to_thread)."""
        query_job = self._client.query(query, job_config=job_config)
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

            if not self._client:
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
                SELECT news_id, MAX(updated_at) AS updated_at
                FROM `{self._TABLE_ID}`
                WHERE news_id IN UNNEST(@news_ids)
                GROUP BY news_id
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
        """Append fully enriched items into BigQuery using an INSERT statement."""
        started_at = datetime.now(tz=timezone.utc)
        try:
            if not items:
                return IngestLoadResult(
                    source=source,
                    status="success",
                    started_at=started_at,
                    completed_at=datetime.now(tz=timezone.utc),
                )

            if not self._client:
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
                INSERT INTO `{self._TABLE_ID}` (
                    news_id, source, title, url, content, author, category, image_url, thumbnail_url, published_at, updated_at, executed_at, status_code, metadata
                )
                SELECT
                    JSON_VALUE(item, '$.news_id'),
                    JSON_VALUE(item, '$.source'),
                    JSON_VALUE(item, '$.title'),
                    JSON_VALUE(item, '$.url'),
                    JSON_VALUE(item, '$.content'),
                    JSON_VALUE(item, '$.author'),
                    JSON_VALUE(item, '$.category'),
                    JSON_VALUE(item, '$.image_url'),
                    JSON_VALUE(item, '$.thumbnail_url'),
                    CAST(JSON_VALUE(item, '$.published_at') AS TIMESTAMP),
                    CAST(JSON_VALUE(item, '$.updated_at') AS TIMESTAMP),
                    CAST(JSON_VALUE(item, '$.executed_at') AS TIMESTAMP),
                    CAST(JSON_VALUE(item, '$.status_code') AS INT64),
                    PARSE_JSON(JSON_EXTRACT(item, '$.metadata'))
                FROM
                    UNNEST(JSON_EXTRACT_ARRAY(@payload, '$')) AS item
            """

            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("payload", "STRING", payload_str)
                ]
            )

            async with self._semaphore:
                await asyncio.to_thread(self._run_query_sync, query, job_config)

            logger.info(
                "[%s] Load completed: %d items successfully appended to BigQuery.",
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
