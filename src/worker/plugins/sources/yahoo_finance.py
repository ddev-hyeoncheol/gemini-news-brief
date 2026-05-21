from typing import ClassVar

from src.models.entities.bronze_news import BronzeNewsModel
from src.models.schemas.ingest import IngestRequest
from src.worker.plugins.sources.base import SourceBase


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
            url = entry.get("link")

            if published_at is None or not url:
                continue

            original_source = entry.get("source", {})
            results.append(
                BronzeNewsModel(
                    executed_at=executed_at,
                    news_id=self.make_news_id(url),
                    category="finance",
                    source=self.source,
                    published_at=published_at,
                    title=entry.get("title", ""),
                    url=url,
                    image_url=self._parse_image_url(entry),
                    updated_at=published_at,
                    metadata={
                        "original_source": original_source.get("title"),
                        "original_source_url": original_source.get("href"),
                        "guid": entry.get("id"),
                    },
                )
            )

        return results
