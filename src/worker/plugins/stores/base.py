import asyncio

from datetime import datetime, timezone
from typing import Any
from google.cloud import bigquery

from src.core.logger import get_logger

logger = get_logger(__name__)


class StoreBase:
    """
    Base class for all database stores.
    Provides common utilities like asynchronous query execution and batch deletion.
    """

    def __init__(
        self, client: bigquery.Client | None, semaphore: asyncio.Semaphore
    ) -> None:
        """Initialize the store with a BigQuery client and a concurrency semaphore."""
        self._client = client
        self._semaphore = semaphore

    async def execute_query(
        self, query: str, job_config: bigquery.QueryJobConfig | None = None
    ) -> Any:
        """Execute a BigQuery query asynchronously with semaphore concurrency control."""
        async with self._semaphore:
            return await asyncio.to_thread(self._run_query_sync, query, job_config)

    async def execute_load_json(
        self,
        json_rows: list[dict[str, Any]],
        destination: str,
        job_config: bigquery.LoadJobConfig | None = None,
    ) -> Any:
        """Execute a BigQuery JSON load job asynchronously with semaphore concurrency control."""

        # BigQuery Load API ignores defaultValueExpression (e.g. CURRENT_TIMESTAMP())
        # when the field is absent or explicitly set to null in the payload.
        # Inject 'loaded_at' here so it is applied consistently across all tables.
        load_time = datetime.now(tz=timezone.utc).isoformat()
        enriched_rows = [
            {**row, "loaded_at": load_time} if not row.get("loaded_at") else row
            for row in json_rows
        ]

        async with self._semaphore:
            return await asyncio.to_thread(
                self._run_load_json_sync, enriched_rows, destination, job_config
            )

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

        logger.info(
            "Batch delete started | table: %s, executed_at: %s",
            table_id,
            executed_at.isoformat(),
        )
        await self.execute_query(query, job_config)

    def _get_client(self) -> bigquery.Client:
        """Return the BigQuery client, raising RuntimeError if not initialized."""
        if self._client is None:
            raise RuntimeError(
                "BigQuery client is not initialized. Check GCP credentials."
            )
        return self._client

    def _run_query_sync(
        self, query: str, job_config: bigquery.QueryJobConfig | None = None
    ) -> Any:
        """Execute a BigQuery job synchronously."""
        query_job = self._get_client().query(query, job_config=job_config)
        return query_job.result()

    def _run_load_json_sync(
        self,
        json_rows: list[dict[str, Any]],
        destination: str,
        job_config: bigquery.LoadJobConfig | None = None,
    ) -> Any:
        """Execute a BigQuery JSON load job synchronously."""
        load_job = self._get_client().load_table_from_json(
            json_rows, destination, job_config=job_config
        )
        return load_job.result()
