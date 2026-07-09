import asyncio
from collections.abc import Sequence
from datetime import datetime, timezone

from fastapi import Depends

from src.core.dependencies import get_source_semaphore
from src.core.logger import get_logger
from src.models.schemas.batch import (
    BatchLayer,
    BatchPhase,
    BatchPipelineResponse,
    BatchResponse,
    BatchSourceResult,
    BatchTarget,
)
from src.worker.plugins.source import SourcePlugin
from src.worker.plugins.sources.yahoo_finance import YahooFinanceSource

logger = get_logger(__name__)


class BatchService:
    """Batch service that runs a requested pipeline execution."""

    def __init__(
        self,
        source_plugins: Sequence[SourcePlugin],
    ) -> None:
        """Initialize the batch service with required plugins/dependencies."""
        self.source_plugins = source_plugins

    async def run_pipeline(self, executed_at: datetime) -> BatchPipelineResponse:
        """Run the news batch pipeline."""
        started_at = datetime.now(tz=timezone.utc)
        executed_at = self._resolve_executed_at(executed_at=executed_at)
        logger.info("BatchService batch_pipeline started | executed_at: %s", executed_at.isoformat())

        tasks: list[BatchResponse] = []

        pipeline_tasks = ((BatchLayer.BRONZE, BatchTarget.NEWS),)

        for layer, target in pipeline_tasks:
            tasks.append(await self.run(layer=layer, target=target, executed_at=executed_at))

        completed_at = datetime.now(tz=timezone.utc)
        elapsed_seconds = (completed_at - started_at).total_seconds()

        result = self._create_pipeline_response(
            executed_at=executed_at,
            started_at=started_at,
            completed_at=completed_at,
            elapsed_seconds=elapsed_seconds,
            tasks=tasks,
        )

        logger.info(
            "BatchService batch_pipeline completed | executed_at: %s, status: %s, elapsed: %.2fs",
            executed_at.isoformat(),
            result.status,
            elapsed_seconds,
        )
        return result

    async def run(
        self,
        layer: BatchLayer,
        target: BatchTarget,
        executed_at: datetime,
    ) -> BatchResponse:
        """Run a batch execution by layer and target."""
        executed_at = self._resolve_executed_at(executed_at=executed_at)
        logger.info(
            "BatchService batch started | layer: %s, target: %s, executed_at: %s",
            layer.value,
            target.value,
            executed_at.isoformat(),
        )

        if (layer, target) == (BatchLayer.BRONZE, BatchTarget.NEWS):
            return await self._run_bronze_news(executed_at=executed_at)

        raise ValueError(f"Unsupported batch execution: {layer.value}/{target.value}")

    async def _run_bronze_news(self, executed_at: datetime) -> BatchResponse:
        """Fetch news and load to Bronze layer."""
        started_at = datetime.now(tz=timezone.utc)

        source_results = await asyncio.gather(
            *[
                self._run_bronze_news_source(source_plugin=plugin, executed_at=executed_at)
                for plugin in self.source_plugins
            ]
        )

        count = sum(r.count for r in source_results)

        if not source_results or all(r.status == "success" for r in source_results):
            overall_status = "success"
        elif all(r.status == "failed" for r in source_results):
            overall_status = "failed"
        else:
            overall_status = "partial"

        completed_at = datetime.now(tz=timezone.utc)
        elapsed_seconds = (completed_at - started_at).total_seconds()
        logger.info(
            "BatchService bronze_news completed | executed_at: %s, status: %s, count: %d, elapsed: %.2fs",
            executed_at.isoformat(),
            overall_status,
            count,
            elapsed_seconds,
        )

        return BatchResponse(
            layer=BatchLayer.BRONZE,
            target=BatchTarget.NEWS,
            executed_at=executed_at,
            status=overall_status,
            count=count,
            started_at=started_at,
            completed_at=completed_at,
            elapsed_seconds=elapsed_seconds,
            details=source_results,
        )

    async def _run_bronze_news_source(self, source_plugin: SourcePlugin, executed_at: datetime) -> BatchSourceResult:
        """Process a single source pipeline from RSS fetch to Bronze load."""
        source = source_plugin.source
        started_at = datetime.now(tz=timezone.utc)
        current_phase: BatchPhase = "fetch"
        logger.info(
            "BatchService bronze_news_source started | executed_at: %s, source: %s",
            executed_at.isoformat(),
            source,
        )

        try:
            # 1. Fetch
            current_phase = "fetch"
            fetch_items = await source_plugin.run_fetch(executed_at=executed_at)

            # 2. Entry lookup
            current_phase = "entry_lookup"
            lookup_items = await self.db_plugin.run_lookup_bronze_news(
                executed_at=executed_at,
                source=source,
                items=fetch_items,
                lookup_key="entry_id",
            )

            # 3. Enrich
            current_phase = "enrich"
            enriched_items = await source_plugin.run_enrich(items=lookup_items)

            # Detect item-level enrich failures before database lookup.
            has_enrich_failure = any(item.status_code != 200 or not item.content for item in enriched_items)

            # 4. News lookup
            current_phase = "news_lookup"
            final_items = await self.db_plugin.run_lookup_bronze_news(
                executed_at=executed_at,
                source=source,
                items=enriched_items,
                lookup_key="news_id",
            )

            # 5. Load
            current_phase = "load"
            await self.db_plugin.run_load_bronze_news(
                source=source,
                items=final_items,
            )

            status = "partial" if has_enrich_failure else "success"
            completed_at = datetime.now(tz=timezone.utc)
            elapsed_seconds = (completed_at - started_at).total_seconds()
            logger.info(
                "BatchService bronze_news_source completed | executed_at: %s, source: %s, status: %s, count: %d, elapsed: %.2fs",
                executed_at.isoformat(),
                source,
                status,
                len(final_items),
                elapsed_seconds,
            )

            return BatchSourceResult(
                source=source,
                executed_at=executed_at,
                status=status,
                count=len(final_items),
                started_at=started_at,
                completed_at=completed_at,
                elapsed_seconds=elapsed_seconds,
            )
        except Exception as e:
            completed_at = datetime.now(tz=timezone.utc)
            elapsed_seconds = (completed_at - started_at).total_seconds()
            logger.exception(
                "BatchService bronze_news_source failed | executed_at: %s, source: %s, failed_phase: %s, elapsed: %.2fs, error: %s",
                executed_at.isoformat(),
                source,
                current_phase,
                elapsed_seconds,
                str(e),
            )
            return BatchSourceResult(
                source=source,
                executed_at=executed_at,
                status="failed",
                started_at=started_at,
                completed_at=completed_at,
                elapsed_seconds=elapsed_seconds,
                failed_phase=current_phase,
                error_message=f"{type(e).__name__}::{e}",
            )

    def _resolve_executed_at(self, executed_at: datetime) -> datetime:
        """Return the normalized batch execution time floored to the nearest 10-minute UTC."""
        utc_dt = executed_at.astimezone(timezone.utc)
        return utc_dt.replace(second=0, microsecond=0, minute=(utc_dt.minute // 10) * 10)

    def _create_pipeline_response(
        self,
        executed_at: datetime,
        started_at: datetime,
        completed_at: datetime,
        elapsed_seconds: float,
        tasks: list[BatchResponse],
    ) -> BatchPipelineResponse:
        """Create a BatchPipelineResponse from task execution results."""
        statuses = [task.status for task in tasks]

        if any(task_status == "failed" for task_status in statuses):
            overall_status = "failed"
        elif any(task_status == "partial" for task_status in statuses):
            overall_status = "partial"
        else:
            overall_status = "success"

        return BatchPipelineResponse(
            executed_at=executed_at,
            status=overall_status,
            started_at=started_at,
            completed_at=completed_at,
            elapsed_seconds=elapsed_seconds,
            tasks=tasks,
        )

    def _create_failed_response(
        self,
        layer: BatchLayer,
        target: BatchTarget,
        executed_at: datetime,
        started_at: datetime,
        completed_at: datetime | None,
        failed_phase: BatchPhase,
        error_message: str | None,
    ) -> BatchResponse:
        """Create and return a failed BatchResponse."""
        completed_at = completed_at or datetime.now(tz=timezone.utc)
        elapsed_seconds = (completed_at - started_at).total_seconds()
        return BatchResponse(
            layer=layer,
            target=target,
            executed_at=executed_at,
            status="failed",
            started_at=started_at,
            completed_at=completed_at,
            elapsed_seconds=elapsed_seconds,
            failed_phase=failed_phase,
            error_message=error_message,
        )


def get_batch_service(
    source_semaphore: asyncio.Semaphore = Depends(get_source_semaphore),
) -> BatchService:
    """Provide FastAPI dependency for BatchService."""
    source_plugins = [
        YahooFinanceSource(semaphore=source_semaphore),
    ]

    return BatchService(source_plugins=source_plugins)
