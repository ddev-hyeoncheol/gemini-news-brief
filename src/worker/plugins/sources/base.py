import asyncio
import hashlib
import random

import feedparser
import httpx
import newspaper

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, ClassVar

from src.models.entities.news import BronzeNewsModel
from src.models.schemas.ingest import IngestRequest

_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"


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

    async def enrich(self, url: str) -> dict[str, Any]:
        """
        Fetch and parse full article content.

        Use httpx for async I/O to get status_code and HTML,
        then use newspaper3k for CPU-bound text extraction.
        Return a dict with author, content, thumbnail_url, status_code, and error_message.
        Limit concurrent requests across all sources using the shared semaphore.
        """
        max_retries = 2
        result: dict[str, Any] = {}

        for attempt in range(max_retries + 1):
            async with self._semaphore:
                # Add a random delay (jitter) between 0.1 and 0.5 seconds to prevent rate limiting.
                await asyncio.sleep(random.uniform(0.1, 0.5))
                status_code, html, error_message = await self._fetch_html(url)

                # Define the default result structure.
                result = {
                    "author": None,
                    "content": None,
                    "thumbnail_url": None,
                    "status_code": status_code,
                    "error_message": error_message,
                }

                # Attempt to parse only if the response is successful (200 OK) and HTML is present.
                if status_code == 200 and html:
                    try:
                        # Pass the downloaded HTML to newspaper3k parser.
                        parsed = await asyncio.to_thread(
                            self._parse_article_html, url, html
                        )
                        result.update(
                            {
                                "author": parsed.get("author"),
                                "content": parsed.get("content"),
                                "thumbnail_url": parsed.get("thumbnail_url"),
                            }
                        )
                    # Parsing failed but HTTP request was successful.
                    except Exception as e:
                        result["error_message"] = (
                            f"Parsing failed: {type(e).__name__} - {str(e)}"
                        )

            # Check if we should retry (outside the semaphore lock).
            if status_code in (0, 500, 502, 503, 504) and attempt < max_retries:
                await asyncio.sleep(5.0)
                continue

            return result

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

    async def _fetch_html(self, url: str) -> tuple[int, str | None, str | None]:
        """Fetch HTML content asynchronously using httpx."""
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(
                    url,
                    headers={"User-Agent": self._user_agent},
                    timeout=10.0,
                )
                return response.status_code, response.text, None
        except Exception as e:
            # Network error or unexpected exception before receiving an HTTP response.
            return 0, None, f"Network error: {type(e).__name__} - {str(e)}"

    def _parse_article_html(self, url: str, html: str) -> dict[str, str | None]:
        """Extract text and metadata from raw HTML synchronously using newspaper3k."""
        article = newspaper.Article(url, config=self._newspaper_config)
        article.set_html(html)
        article.parse()

        if not article.text:
            raise ValueError("Failed to extract article content (empty text).")

        return {
            "author": ", ".join(article.authors) if article.authors else None,
            "content": article.text,
            "thumbnail_url": article.top_image or None,
        }

    def _parse_published_at(self, entry: feedparser.FeedParserDict) -> datetime | None:
        """Parse published_at from feedparser time struct as UTC datetime."""
        published_parsed = entry.get("published_parsed")
        if published_parsed is None:
            return None
        return datetime(*published_parsed[:6], tzinfo=timezone.utc)
