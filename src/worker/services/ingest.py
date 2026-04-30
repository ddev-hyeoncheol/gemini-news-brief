import asyncio

from datetime import datetime, timezone

from src.core.logger import get_logger
from src.models.schemas.ingest import (
    IngestRequest,
    IngestResponse,
    IngestSourceResult,
)
from src.worker.plugins.collect import CollectPlugin
from src.worker.plugins.bigquery import BigQueryPlugin
from src.worker.plugins.sources.yahoo_finance import YahooFinanceSource

logger = get_logger(__name__)


class IngestService:
    """Orchestrates parallel news collection and loading across all registered sources."""

    def __init__(
        self, source_plugins: list[CollectPlugin], db_plugin: BigQueryPlugin
    ) -> None:
        """Initialize the service with a list of source plugins and a database plugin."""
        self.source_plugins = source_plugins
        self.db_plugin = db_plugin

    async def run(self, request: IngestRequest) -> IngestResponse:
        """Run all plugins in parallel and aggregate results into IngestResponse."""
        source_results: list[IngestSourceResult] = await asyncio.gather(
            *[self._run_pipeline(plugin, request) for plugin in self.source_plugins]
        )

        target_count = sum(r.target_count for r in source_results)
        collected_count = sum(r.collected_count for r in source_results)
        loaded_count = sum(r.loaded_count for r in source_results)
        success_count = sum(1 for r in source_results if r.status == "success")

        if not source_results or success_count == len(source_results):
            status = "success"
        elif success_count == 0:
            status = "failed"
        else:
            status = "partial"

        return IngestResponse(
            executed_at=request.executed_at,
            status=status,
            target_count=target_count,
            collected_count=collected_count,
            loaded_count=loaded_count,
            sources=list(source_results),
        )

    async def _run_pipeline(
        self, plugin: CollectPlugin, request: IngestRequest
    ) -> IngestSourceResult:
        """Process a single source pipeline (collect -> load), returning a combined IngestSourceResult."""
        # 1. Collect Phase (Errors are handled internally by the plugin)
        collect_result = await plugin.execute(request)

        if collect_result.status == "failed":
            return IngestSourceResult(
                source=collect_result.source,
                status="failed",
                target_count=collect_result.target_count,
                collected_count=collect_result.collected_count,
                collect_started_at=collect_result.started_at,
                collected_at=collect_result.collected_at,
                failed_phase="collect",
                error_message=collect_result.error_message,
            )

        # 2. Load Phase
        load_result = await self.db_plugin.execute(
            collect_result.source, collect_result.items
        )

        return IngestSourceResult(
            source=collect_result.source,
            status=load_result.status,
            target_count=collect_result.target_count,
            collected_count=collect_result.collected_count,
            loaded_count=load_result.loaded_count,
            collect_started_at=collect_result.started_at,
            collected_at=collect_result.collected_at,
            load_started_at=load_result.started_at,
            loaded_at=load_result.loaded_at,
            failed_phase="load" if load_result.status == "failed" else None,
            error_message=load_result.error_message,
        )


# Module-level singleton: instantiated once at import time.
# Cloud Run scale-to-zero means each instance starts fresh,
# so module-level state is safe and avoids lifespan overhead.
_source_semaphore = asyncio.Semaphore(10)
_db_semaphore = asyncio.Semaphore(10)

_ingest_service = IngestService(
    source_plugins=[
        CollectPlugin(source=YahooFinanceSource(semaphore=_source_semaphore)),
    ],
    db_plugin=BigQueryPlugin(semaphore=_db_semaphore),
)


def get_ingest_service() -> IngestService:
    """FastAPI dependency provider for IngestService."""
    return _ingest_service
