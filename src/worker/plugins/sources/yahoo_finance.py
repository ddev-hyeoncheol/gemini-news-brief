import asyncio
import feedparser

from typing import ClassVar

from src.core.logger import get_logger
from src.models.entities.news import BronzeNewsModel
from src.models.schemas.collect import CollectRequest
from src.worker.plugins.sources.base import SourceBase

logger = get_logger(__name__)


class YahooFinanceSource(SourceBase):
    """News source for Yahoo Finance RSS feed (https://finance.yahoo.com/rss/)."""

    source_name: ClassVar[str] = "yahoo_finance"
    RSS_URL: ClassVar[str] = "https://finance.yahoo.com/rss/"

    async def parse(
        self, feed: feedparser.FeedParserDict, request: CollectRequest
    ) -> list[BronzeNewsModel]:
        """Parse and enrich feed entries into BronzeNewsModel within the time window."""
        collected_at = self.now_utc()

        # Filter entries within the time window first
        candidates = []
        for entry in feed.entries:
            published_at = self._parse_published_at(entry)
            if published_at is not None and self.is_within_window(
                published_at, request
            ):
                candidates.append((entry, published_at))

        # Enrich all candidates in parallel via newspaper3k
        enrichments = await asyncio.gather(
            *[self.enrich(entry.get("link", "")) for entry, _ in candidates]
        )

        results: list[BronzeNewsModel] = []
        for (entry, published_at), enriched in zip(candidates, enrichments):
            original_source = entry.get("source", {})
            results.append(
                BronzeNewsModel(
                    news_id=self.make_news_id(entry.get("link", "")),
                    source=self.source_name,
                    title=entry.get("title", ""),
                    url=entry.get("link", ""),
                    image_url=self._parse_image_url(entry),
                    thumbnail_url=enriched["thumbnail_url"],
                    content=enriched["content"],
                    author=enriched["author"],
                    published_at=published_at,
                    collected_at=collected_at,
                    metadata={
                        "original_source": original_source.get("value"),
                        "original_source_url": original_source.get("url"),
                        "guid": entry.get("id"),
                    },
                )
            )

        return results
