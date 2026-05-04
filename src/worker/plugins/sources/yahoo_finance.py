from typing import ClassVar

from src.core.logger import get_logger
from src.models.entities.news import BronzeNewsModel
from src.models.schemas.ingest import IngestRequest
from src.worker.plugins.sources.base import SourceBase

logger = get_logger(__name__)


class YahooFinanceSource(SourceBase):
    """News source for Yahoo Finance RSS feed (https://finance.yahoo.com/rss/)."""

    source: ClassVar[str] = "yahoo_finance"
    RSS_URL: ClassVar[str] = "https://finance.yahoo.com/rss/"

    async def fetch(self, request: IngestRequest) -> list[BronzeNewsModel]:
        """Fetch raw RSS feed and map to BronzeNewsModel entities without enrichment."""
        executed_at = request.executed_at

        feed = await self._fetch_feed()

        results: list[BronzeNewsModel] = []
        for entry in feed.entries:
            published_at = self._parse_published_at(entry)
            if published_at is None:
                continue

            original_source = entry.get("source", {})
            results.append(
                BronzeNewsModel(
                    news_id=self.make_news_id(entry.get("link", "")),
                    source=self.source,
                    title=entry.get("title", ""),
                    url=entry.get("link", ""),
                    image_url=self._parse_image_url(entry),
                    published_at=published_at,
                    updated_at=published_at,
                    executed_at=executed_at,
                    metadata={
                        "original_source": original_source.get("title"),
                        "original_source_url": original_source.get("href"),
                        "guid": entry.get("id"),
                    },
                )
            )

        return results
