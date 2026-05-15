import asyncio

from datetime import datetime, timezone
from typing import Any
from google.cloud import bigquery

from src.providers.bigquery import BigQueryProvider
from src.core.logger import get_logger

logger = get_logger(__name__)


class StoreBase:
    """
    Base class for all database stores.
    Provides common utilities like asynchronous query execution and batch deletion.
    """

    def __init__(self, bigquery_provider: BigQueryProvider) -> None:
        """Initialize the store with a BigQuery provider."""
        self._bigquery_provider = bigquery_provider

    async def execute_query(
        self, query: str, job_config: bigquery.QueryJobConfig | None = None
    ) -> Any:
        """Execute a BigQuery query asynchronously with semaphore concurrency control."""
        async with self._bigquery_provider.semaphore:
            return await asyncio.to_thread(self._run_query_sync, query, job_config)

    async def execute_load_json(
        self,
        json_rows: list[dict[str, Any]],
        table_id: str,
        job_config: bigquery.LoadJobConfig | None = None,
    ) -> Any:
        """Execute a BigQuery JSON load job asynchronously with semaphore concurrency control."""
        if not json_rows:
            logger.info("Batch load skipped | table: %s, reason: no items", table_id)
            return None

        # BigQuery Load API does not evaluate defaultValueExpression at load time.
        # Overwrite 'loaded_at' with the current UTC timestamp for every row.
        loaded_at = datetime.now(tz=timezone.utc).isoformat()
        json_rows = [{**row, "loaded_at": loaded_at} for row in json_rows]

        async with self._bigquery_provider.semaphore:
            result = await asyncio.to_thread(
                self._run_load_json_sync, json_rows, table_id, job_config
            )

        logger.info(
            "Batch load completed | table: %s, count: %d",
            table_id,
            len(json_rows),
        )
        return result

    async def execute_delete_batch(self, table_id: str, executed_at: datetime) -> None:
        """
        Delete previously loaded data for a specific batch execution time.
        Ensure idempotency for Silver and Gold layer data loads.
        """
        query = f"DELETE FROM `{table_id}` WHERE executed_at = @executed_at"
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("executed_at", "TIMESTAMP", executed_at)
            ]
        )

        results = await self.execute_query(query, job_config)
        deleted_count = getattr(results, "num_dml_affected_rows", 0) or 0

        logger.info(
            "Batch delete completed | table: %s, deleted_count: %d",
            table_id,
            deleted_count,
        )

    def _get_client(self) -> bigquery.Client:
        """Return the BigQuery client, raising RuntimeError if not initialized."""
        # Delegate client retrieval to the provider.
        return self._bigquery_provider.get_client()

    def _run_query_sync(
        self, query: str, job_config: bigquery.QueryJobConfig | None = None
    ) -> Any:
        """Execute a BigQuery job synchronously."""
        query_job = self._get_client().query(query, job_config=job_config)
        return query_job.result()

    def _run_load_json_sync(
        self,
        json_rows: list[dict[str, Any]],
        table_id: str,
        job_config: bigquery.LoadJobConfig | None = None,
    ) -> Any:
        """Execute a BigQuery JSON load job synchronously."""
        load_job = self._get_client().load_table_from_json(
            json_rows, destination=table_id, job_config=job_config
        )
        return load_job.result()
