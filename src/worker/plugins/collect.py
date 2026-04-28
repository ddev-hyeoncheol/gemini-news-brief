from src.core.logger import get_logger
from src.models.entities.news import BronzeNewsModel
from src.models.schemas.collect import CollectRequest
from src.worker.plugins.base import BasePlugin
from src.worker.plugins.sources.base import SourceBase

logger = get_logger(__name__)


class CollectPlugin(BasePlugin):
    """
    Plugin that orchestrates news collection using an injected Source.

    Receives a SourceBase instance via constructor (composition),
    delegates collect() and parse() to the source.
    """

    def __init__(self, source: SourceBase) -> None:
        self.source = source

    async def execute(self, request: CollectRequest) -> list[BronzeNewsModel]:
        """Run collect → parse flow and return results."""
        raw = await self.source.collect()
        results = await self.source.parse(raw, request)
        logger.info(
            "%s collected %d items within window", self.source.source_name, len(results)
        )
        return results
