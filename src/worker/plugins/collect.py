from datetime import datetime, timezone
from typing import Any

from src.core.logger import get_logger
from src.models.schemas.ingest import IngestRequest, IngestCollectResult
from src.worker.plugins.base import BasePlugin
from src.worker.plugins.sources.base import SourceBase

logger = get_logger(__name__)


class CollectPlugin(BasePlugin):
    """
    Plugin that orchestrates news collection using an injected Source.

    Receives a SourceBase instance via constructor (composition),
    and delegates collect() and parse() executions to the source.
    """

    def __init__(self, source: SourceBase) -> None:
        """Initialize the collection plugin with a specific news source."""
        self.source = source

    async def execute(
        self, request: IngestRequest, *args: Any, **kwargs: Any
    ) -> IngestCollectResult:
        """Run collect → parse flow and return an IngestCollectResult."""
        started_at = datetime.now(tz=timezone.utc)
        try:
            raw = await self.source.collect()
            parsed = await self.source.parse(raw, request)

            logger.info(
                "%s collected %d/%d items within window",
                self.source.source,
                len(parsed.items),
                parsed.target_count,
            )
            return IngestCollectResult(
                source=self.source.source,
                status="success",
                items=parsed.items,
                target_count=parsed.target_count,
                collected_count=len(parsed.items),
                started_at=started_at,
                collected_at=datetime.now(tz=timezone.utc),
            )
        except Exception as e:
            logger.exception("Collection failed for source=%s", self.source.source)
            return IngestCollectResult(
                source=self.source.source,
                status="failed",
                started_at=started_at,
                collected_at=datetime.now(tz=timezone.utc),
                error_message=str(e),
            )
