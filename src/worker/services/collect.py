import asyncio

from datetime import datetime, timezone

from src.core.logger import get_logger
from src.models.schemas.collect import (
    CollectRequest,
    CollectResponse,
    CollectSourceResult,
)
from src.worker.plugins.collect import CollectPlugin
from src.worker.plugins.sources.yahoo_finance import YahooFinanceSource

logger = get_logger(__name__)


class CollectService:
    """Orchestrates parallel news collection across all registered CollectPlugins."""

    def __init__(self, plugins: list[CollectPlugin]) -> None:
        self.plugins = plugins

    async def run(self, request: CollectRequest) -> CollectResponse:
        """Run all plugins in parallel and aggregate results into CollectResponse."""
        source_results: list[CollectSourceResult] = await asyncio.gather(
            *[self._run_plugin(plugin, request) for plugin in self.plugins]
        )

        total_count = sum(r.total_count for r in source_results)
        saved_count = sum(r.saved_count for r in source_results)

        success_count = sum(1 for r in source_results if r.status == "success")
        if success_count == len(source_results):
            status = "success"
        elif success_count == 0:
            status = "failed"
        else:
            status = "partial"

        return CollectResponse(
            scheduled_at=request.scheduled_at,
            status=status,
            total_count=total_count,
            saved_count=saved_count,
            sources=list(source_results),
        )

    async def _run_plugin(
        self, plugin: CollectPlugin, request: CollectRequest
    ) -> CollectSourceResult:
        """Run a single CollectPlugin and return its CollectSourceResult."""
        started_at = datetime.now(tz=timezone.utc)
        try:
            results = await plugin.execute(request)
            return CollectSourceResult(
                name=plugin.source.source_name,
                status="success",
                total_count=len(results),
                saved_count=len(results),  # TODO: update after BigQuery dedup
                started_at=started_at,
                completed_at=datetime.now(tz=timezone.utc),
            )
        except Exception as e:
            logger.exception(
                "Collection failed for source=%s", plugin.source.source_name
            )
            return CollectSourceResult(
                name=plugin.source.source_name,
                status="failed",
                total_count=0,
                saved_count=0,
                started_at=started_at,
                completed_at=datetime.now(tz=timezone.utc),
                error_message=str(e),
            )


# Module-level singleton: instantiated once at import time.
# Cloud Run scale-to-zero means each instance starts fresh,
# so module-level state is safe and avoids lifespan overhead.
_semaphore = asyncio.Semaphore(10)
_collect_service = CollectService(
    plugins=[
        CollectPlugin(source=YahooFinanceSource(semaphore=_semaphore)),
    ]
)


def get_collect_service() -> CollectService:
    """FastAPI dependency provider for CollectService."""
    return _collect_service
