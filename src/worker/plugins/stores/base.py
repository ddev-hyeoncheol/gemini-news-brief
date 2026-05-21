import asyncio
from collections.abc import Sequence
from datetime import date, datetime, timezone
from typing import Any, TypeVar

from google.cloud import bigquery
from pydantic import BaseModel

from src.core.logger import get_logger
from src.providers.bigquery import BigQueryProvider

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class StoreBase:
    """
    Base class for all database stores.
    Provides common utilities for BigQuery execution and model record operations.
    """

    def __init__(self, bigquery_provider: BigQueryProvider) -> None:
        """Initialize the store with a BigQuery provider."""
        self._bigquery_provider = bigquery_provider

    async def extract_models(
        self,
        table_id: str,
        model_class: type[T],
        filters: dict[str, Any],
    ) -> list[T]:
        """Extract model records matching trusted store-defined filters."""
        where_sql, job_config = self._build_filter_clause(filters)
        query = f"""
            SELECT *
            FROM `{table_id}`
            WHERE {where_sql}
        """

        results = await self.execute_query(query, job_config)
        items = [model_class(**dict(row)) for row in results]

        logger.info(
            "Store extract completed | table: %s, count: %d",
            table_id,
            len(items),
        )
        return items

    async def load_models(self, table_id: str, items: Sequence[BaseModel]) -> None:
        """Load Pydantic model records into a BigQuery table."""
        json_rows = [item.model_dump(mode="json") for item in items]
        await self.execute_load_json(json_rows=json_rows, table_id=table_id)

    async def delete_models(self, table_id: str, filters: dict[str, Any]) -> None:
        """Delete model records matching trusted store-defined filters."""
        where_sql, job_config = self._build_filter_clause(filters)
        query = f"""
            DELETE FROM `{table_id}`
            WHERE {where_sql}
        """

        results = await self.execute_query(query, job_config)
        deleted_count = getattr(results, "num_dml_affected_rows", 0) or 0

        logger.info(
            "Store delete completed | table: %s, count: %d",
            table_id,
            deleted_count,
        )

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
            logger.info(
                "Store load skipped | table: %s, reason: no items",
                table_id,
            )
            return None

        # BigQuery Load API does not evaluate default value expressions during JSON loads.
        # Overwrite 'loaded_at' with the current UTC timestamp for every row.
        loaded_at = datetime.now(tz=timezone.utc).isoformat()
        json_rows = [{**row, "loaded_at": loaded_at} for row in json_rows]

        async with self._bigquery_provider.semaphore:
            result = await asyncio.to_thread(
                self._run_load_json_sync, json_rows, table_id, job_config
            )

        logger.info(
            "Store load completed | table: %s, count: %d",
            table_id,
            len(json_rows),
        )
        return result

    def _build_filter_clause(
        self, filters: dict[str, Any]
    ) -> tuple[str, bigquery.QueryJobConfig]:
        """Build a parameterized BigQuery WHERE clause from trusted filters."""
        if not filters:
            raise ValueError("filters must contain at least one condition")

        clauses = []
        query_parameters = []
        for index, (column, value) in enumerate(filters.items()):
            if value is None:
                clauses.append(f"{column} IS NULL")
                continue

            parameter_name = f"filter_{index}"
            clauses.append(f"{column} = @{parameter_name}")
            query_parameters.append(
                self._make_scalar_query_parameter(parameter_name, value)
            )

        return " AND ".join(clauses), bigquery.QueryJobConfig(
            query_parameters=query_parameters
        )

    def _make_scalar_query_parameter(
        self, name: str, value: Any
    ) -> bigquery.ScalarQueryParameter:
        """Return a BigQuery scalar query parameter for a supported Python value."""
        if isinstance(value, datetime):
            return bigquery.ScalarQueryParameter(name, "TIMESTAMP", value)
        if isinstance(value, bool):
            return bigquery.ScalarQueryParameter(name, "BOOL", value)
        if isinstance(value, int):
            return bigquery.ScalarQueryParameter(name, "INT64", value)
        if isinstance(value, float):
            return bigquery.ScalarQueryParameter(name, "FLOAT64", value)
        if isinstance(value, str):
            return bigquery.ScalarQueryParameter(name, "STRING", value)
        if isinstance(value, date):
            return bigquery.ScalarQueryParameter(name, "DATE", value)

        raise TypeError(f"Unsupported filter value type: {type(value).__name__}")

    def _get_client(self) -> bigquery.Client:
        """Return the BigQuery client, raising RuntimeError if not initialized."""
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
