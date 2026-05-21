import asyncio
from datetime import datetime, timezone

from fastapi import Depends

from src.core.dependencies import get_bigquery_provider, get_source_semaphore
from src.models.schemas.ingest import (
    IngestRequest,
    IngestResponse,
    IngestSourceResult,
    IngestTarget,
)
from src.providers.bigquery import BigQueryProvider
from src.worker.plugins.bigquery import IngestDbPlugin
from src.worker.plugins.collect import CollectPlugin
from src.worker.plugins.sources.yahoo_finance import YahooFinanceSource
from src.worker.plugins.stores.bronze import BronzeStore


class IngestService:
    """Orchestrate parallel news collection and loading across all registered sources."""

    def __init__(
        self, source_plugins: list[CollectPlugin], db_plugin: IngestDbPlugin
    ) -> None:
        """Initialize the service with a list of source plugins and a database plugin."""
        self.source_plugins = source_plugins
        self.db_plugin = db_plugin

    async def run(self, target: IngestTarget, request: IngestRequest) -> IngestResponse:
        """Run all plugins in parallel and aggregate results into IngestResponse."""
        source_results: list[IngestSourceResult] = await asyncio.gather(
            *[self._run_pipeline(plugin, request) for plugin in self.source_plugins]
        )

        fetched_count = sum(r.fetched_count for r in source_results)
        lookup_count = sum(r.lookup_count for r in source_results)
        enriched_count = sum(r.enriched_count for r in source_results)
        loaded_count = sum(r.loaded_count for r in source_results)

        success_count = sum(1 for r in source_results if r.status == "success")
        failed_count = sum(1 for r in source_results if r.status == "failed")

        if not source_results or success_count == len(source_results):
            status = "success"
        elif failed_count == len(source_results):
            status = "failed"
        else:
            status = "partial"

        return IngestResponse(
            executed_at=request.executed_at,
            status=status,
            fetched_count=fetched_count,
            lookup_count=lookup_count,
            enriched_count=enriched_count,
            loaded_count=loaded_count,
            sources=list(source_results),
        )

    async def _run_pipeline(
        self, plugin: CollectPlugin, request: IngestRequest
    ) -> IngestSourceResult:
        """Process a single source pipeline (fetch -> lookup -> enrich -> load)."""
        source = plugin.source
        started_at = datetime.now(tz=timezone.utc)

        # 1. Fetch phase.
        fetch_res = await plugin.fetch(request)
        if fetch_res.status == "failed":
            return IngestSourceResult(
                source=source,
                status="failed",
                started_at=started_at,
                completed_at=datetime.now(tz=timezone.utc),
                failed_phase="fetch",
                error_message=fetch_res.error_message,
            )

        # 2. Lookup phase.
        lookup_res = await self.db_plugin.lookup(source=source, items=fetch_res.items)
        if lookup_res.status == "failed":
            return IngestSourceResult(
                source=source,
                status="failed",
                fetched_count=fetch_res.item_count,
                started_at=started_at,
                completed_at=datetime.now(tz=timezone.utc),
                failed_phase="lookup",
                error_message=lookup_res.error_message,
            )

        # 3. Enrich phase.
        enrich_res = await plugin.enrich(lookup_res.items)
        if enrich_res.status == "failed":
            return IngestSourceResult(
                source=source,
                status="failed",
                fetched_count=fetch_res.item_count,
                lookup_count=lookup_res.item_count,
                started_at=started_at,
                completed_at=datetime.now(tz=timezone.utc),
                failed_phase="enrich",
                error_message=enrich_res.error_message,
            )

        # 4. Load phase.
        load_res = await self.db_plugin.load(source=source, items=enrich_res.items)

        # Bubble up partial success if load succeeded but enrich was partial.
        status = load_res.status
        if status == "success" and enrich_res.status == "partial":
            status = "partial"

        return IngestSourceResult(
            source=source,
            status=status,
            fetched_count=fetch_res.item_count,
            lookup_count=lookup_res.item_count,
            enriched_count=enrich_res.item_count,
            loaded_count=load_res.item_count,
            started_at=started_at,
            completed_at=datetime.now(tz=timezone.utc),
            failed_phase="load" if load_res.status == "failed" else None,
            error_message=load_res.error_message or enrich_res.error_message,
        )


def get_ingest_service(
    bigquery_provider: BigQueryProvider = Depends(get_bigquery_provider),
    source_semaphore: asyncio.Semaphore = Depends(get_source_semaphore),
) -> IngestService:
    """Provide FastAPI dependency for IngestService."""
    return IngestService(
        source_plugins=[
            CollectPlugin(source=YahooFinanceSource(semaphore=source_semaphore)),
        ],
        db_plugin=IngestDbPlugin(
            store=BronzeStore(bigquery_provider=bigquery_provider)
        ),
    )
