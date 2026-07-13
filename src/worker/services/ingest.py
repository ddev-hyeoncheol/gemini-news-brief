import asyncio
from collections.abc import Sequence
from datetime import datetime, timezone

from fastapi import Depends

from src.core.dependencies import get_source_semaphore
from src.core.logger import get_logger
from src.models.schemas.ingest import IngestPhase, IngestResponse, IngestSourceResult
from src.worker.plugins.rss_source import RssSource
from src.worker.plugins.sources.yahoo_finance import YahooFinanceSource

logger = get_logger(__name__)

# Registry of enabled news source classes. Add a source class here to activate it.
ENABLED_SOURCE_CLASSES: tuple[type[RssSource], ...] = (YahooFinanceSource,)


class IngestService:
    """Ingest service that fetches news from sources and loads the Bronze layer."""

    def __init__(self, source_plugins: Sequence[RssSource]) -> None:
        """Initialize the ingest service with required source plugins."""
        self.source_plugins = source_plugins

    async def run(self, executed_at: datetime) -> IngestResponse:
        """Fetch news from all sources and load to the Bronze layer."""
        executed_at = self._resolve_executed_at(executed_at=executed_at)
        started_at = datetime.now(tz=timezone.utc)
        logger.info("IngestService ingest started | executed_at: %s", executed_at.isoformat())

        source_results = await asyncio.gather(
            *[self._run_source(source_plugin=plugin, executed_at=executed_at) for plugin in self.source_plugins]
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
            "IngestService ingest completed | executed_at: %s, status: %s, count: %d, elapsed: %.2fs",
            executed_at.isoformat(),
            overall_status,
            count,
            elapsed_seconds,
        )

        return IngestResponse(
            executed_at=executed_at,
            status=overall_status,
            count=count,
            started_at=started_at,
            completed_at=completed_at,
            elapsed_seconds=elapsed_seconds,
            details=source_results,
        )

    async def _run_source(self, source_plugin: RssSource, executed_at: datetime) -> IngestSourceResult:
        """Process a single source pipeline from RSS fetch to Bronze load."""
        source = source_plugin.source
        started_at = datetime.now(tz=timezone.utc)
        current_phase: IngestPhase = "fetch"
        logger.info(
            "IngestService source started | executed_at: %s, source: %s",
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
                "IngestService source completed | executed_at: %s, source: %s, status: %s, count: %d, elapsed: %.2fs",
                executed_at.isoformat(),
                source,
                status,
                len(final_items),
                elapsed_seconds,
            )

            return IngestSourceResult(
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
                "IngestService source failed | executed_at: %s, source: %s, failed_phase: %s, elapsed: %.2fs, error: %s",
                executed_at.isoformat(),
                source,
                current_phase,
                elapsed_seconds,
                str(e),
            )
            return IngestSourceResult(
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
        """Return the normalized execution time floored to the nearest 10-minute UTC."""
        utc_dt = executed_at.astimezone(timezone.utc)
        return utc_dt.replace(second=0, microsecond=0, minute=(utc_dt.minute // 10) * 10)


def get_ingest_service(
    source_semaphore: asyncio.Semaphore = Depends(get_source_semaphore),
) -> IngestService:
    """Provide FastAPI dependency for IngestService."""
    source_plugins = [source_cls(semaphore=source_semaphore) for source_cls in ENABLED_SOURCE_CLASSES]

    return IngestService(source_plugins=source_plugins)
