import asyncio
from datetime import datetime, timezone
from typing import Any

from google.cloud import bigquery

from src.config.config import settings
from src.core.logger import get_logger

logger = get_logger(__name__)


class BigQueryProvider:
    """
    Provider class for managing Google BigQuery client and concurrency.
    Handles initialization and provides a shared semaphore for resource throttling.
    """

    def __init__(self, semaphore: asyncio.Semaphore) -> None:
        """
        Initialize the provider with an injected semaphore.
        The semaphore should be created within an async context (e.g., lifespan)
        to ensure it is bound to the correct event loop.
        """
        self._semaphore = semaphore
        self._client = self._init_client()

    async def execute_query(
        self,
        query: str,
        job_config: bigquery.QueryJobConfig | None = None,
    ) -> Any:
        """Execute a BigQuery query asynchronously with semaphore concurrency control."""
        async with self._semaphore:
            return await asyncio.to_thread(self._run_query_sync, query, job_config)

    async def execute_load_json(
        self,
        json_rows: list[dict[str, Any]],
        table_id: str,
        job_config: bigquery.LoadJobConfig | None = None,
    ) -> Any:
        """Execute a BigQuery JSON load job asynchronously with semaphore concurrency control."""
        if not json_rows:
            return None

        # BigQuery Load API does not evaluate default value expressions during JSON loads.
        # Overwrite 'loaded_at' with the UTC timestamp for every row.
        loaded_at = datetime.now(tz=timezone.utc).isoformat()
        json_rows = [{**row, "loaded_at": loaded_at} for row in json_rows]

        async with self._semaphore:
            return await asyncio.to_thread(self._run_load_json_sync, json_rows, table_id, job_config)

    def _init_client(self) -> bigquery.Client | None:
        """Initialize and return a BigQuery client, or None if credentials are not found."""
        is_gcp = settings.is_gcp
        has_explicit_creds = settings.has_explicit_creds

        if not is_gcp and not has_explicit_creds:
            logger.warning(
                "BigQueryProvider initialize failed | reason: GCP environment or explicit credentials not set"
            )
            return None

        try:
            return bigquery.Client(project=settings.gcp_project_id)
        except Exception as e:
            logger.warning("BigQueryProvider initialize failed | error: %s", str(e))
            return None

    def _get_client(self) -> bigquery.Client:
        """Return the BigQuery client, raising RuntimeError if not initialized."""
        if self._client is None:
            raise RuntimeError("BigQuery client is not initialized. Check GCP credentials.")
        return self._client

    def _run_query_sync(
        self,
        query: str,
        job_config: bigquery.QueryJobConfig | None = None,
    ) -> Any:
        """Execute a BigQuery query synchronously."""
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
            json_rows=json_rows, destination=table_id, job_config=job_config
        )
        return load_job.result()
