import asyncio
import hashlib
import feedparser
import newspaper

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, ClassVar

from src.models.entities.news import BronzeNewsModel
from src.models.schemas.ingest import IngestRequest


_USER_AGENT = "Mozilla/5.0 (compatible; GeminiNewsBrief/1.0; +https://github.com/ddev-hyeoncheol/gemini-news-brief)"


class SourceBase(ABC):
    """
    Base class for all independent news source implementations.

    Provides shared utilities:
    - source: Identifies the news source.
    - news_id: Generates a unique hash.
    - Helper methods for RSS fetch, published_at parsing, and image URL extraction.

    Subclasses must implement fetch() for source-specific field mapping.
    """

    source: ClassVar[str]
    RSS_URL: ClassVar[str]

    def __init__(self, semaphore: asyncio.Semaphore) -> None:
        """Initialize with a shared semaphore to limit concurrent enrich requests."""
        self._semaphore = semaphore
        self._user_agent = _USER_AGENT
        self._newspaper_config = newspaper.Config()
        self._newspaper_config.browser_user_agent = self._user_agent
        self._newspaper_config.request_timeout = 10

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if getattr(cls, "__abstractmethods__", None):
            return
        for var in ("source", "RSS_URL"):
            if not isinstance(cls.__dict__.get(var), str):
                raise TypeError(f"{cls.__name__} must define a '{var}' class variable")

    def make_news_id(self, url: str) -> str:
        """Generate a unique news ID by SHA-256 hashing the source and article URL."""
        raw_key = f"{self.source}:{url}"
        return hashlib.sha256(raw_key.encode()).hexdigest()

    @abstractmethod
    async def fetch(self, request: IngestRequest) -> list[BronzeNewsModel]:
        """Fetch raw RSS feed and map to BronzeNewsModel entities WITHOUT enrichment (content is None)."""
        ...

    async def enrich(self, url: str) -> dict[str, str | None]:
        """
        Fetch and parse full article content using newspaper3k.

        Returns a dict with content, author, and thumbnail_url.
        Runs in a thread pool to avoid blocking the event loop.
        Concurrent requests across all sources are limited by the shared semaphore.
        """
        async with self._semaphore:
            return await asyncio.to_thread(self._parse_article, url)

    async def _fetch_feed(self) -> feedparser.FeedParserDict:
        """Helper method to fetch raw RSS feed using feedparser."""
        return await asyncio.to_thread(
            feedparser.parse, self.RSS_URL, agent=self._user_agent
        )

    def _parse_image_url(self, entry: feedparser.FeedParserDict) -> str | None:
        """Extract image URL from media:content tag."""
        media_content = entry.get("media_content")
        if not media_content or not isinstance(media_content, list):
            return None
        return media_content[0].get("url")

    def _parse_article(self, url: str) -> dict[str, str | None]:
        """Download and parse a single article synchronously."""
        try:
            article = newspaper.Article(url, config=self._newspaper_config)
            article.download()
            article.parse()
            return {
                "content": article.text or None,
                "author": ", ".join(article.authors) if article.authors else None,
                "thumbnail_url": article.top_image or None,
            }
        except Exception:
            return {"content": None, "author": None, "thumbnail_url": None}

    def _parse_published_at(self, entry: feedparser.FeedParserDict) -> datetime | None:
        """Parse published_at from feedparser time struct as UTC datetime."""
        published_parsed = entry.get("published_parsed")
        if published_parsed is None:
            return None
        return datetime(*published_parsed[:6], tzinfo=timezone.utc)
