import asyncio
import random
import uuid
from abc import ABC, abstractmethod
from collections.abc import Mapping
from datetime import datetime
from urllib.parse import urlsplit, urlunsplit

import feedparser
import httpx
import newspaper
from tenacity import retry, retry_if_result, stop_after_attempt, wait_fixed

from src.config.config import settings
from src.core.logger import get_logger
from src.core.transient import is_transient_http_status_code
from src.models.entities.bronze_news import BronzeNewsModel
from src.models.schemas.sources.common import SourceEnrichedArticleSchema

logger = get_logger(__name__)


_NAMESPACE_UUID = uuid.uuid5(uuid.NAMESPACE_DNS, "gemini-news-brief")

_retry = retry(
    retry=retry_if_result(lambda res: is_transient_http_status_code(res[0])),
    stop=stop_after_attempt(3),
    wait=wait_fixed(1),
    retry_error_callback=lambda retry_state: retry_state.outcome.result() if retry_state.outcome else None,
)


class SourcePlugin(ABC):
    """
    Abstract base plugin for all independent news source implementations.

    Provides shared utilities and coordinates external news collection:
    - run_fetch(): Source-specific RSS parsing and field mapping.
    - run_enrich(): Standardized parallel scraping with per-item error isolation.
    """

    @property
    @abstractmethod
    def source(self) -> str:
        """Return the news source identifier."""
        pass

    @property
    @abstractmethod
    def RSS_URL(self) -> str:
        """Return the base RSS feed URL."""
        pass

    @property
    def RSS_ENTRY_STORAGE_FIELDS(self) -> set[str]:
        """Return DTO fields mapped to first-class storage columns and excluded from metadata dumps."""
        return set()

    @property
    def RSS_ENTRY_METADATA_FIELDS(self) -> set[str]:
        """Return known source RSS fields intended for metadata after DTO mapping."""
        return set()

    @property
    def RSS_ENTRY_IGNORED_FIELDS(self) -> set[str]:
        """Return RSS fields intentionally ignored by this source."""
        return set()

    @property
    def RSS_ENTRY_KNOWN_FIELDS(self) -> set[str]:
        """Return all known top-level RSS entry fields."""
        return self.RSS_ENTRY_STORAGE_FIELDS | self.RSS_ENTRY_METADATA_FIELDS | self.RSS_ENTRY_IGNORED_FIELDS

    @property
    def BOILERPLATE_CONTENTS(self) -> set[str]:
        """Return a set of known non-article boilerplates to filter out."""
        return set()

    def _is_boilerplate_content(self, content: str | None) -> bool:
        """Return True if extracted content is a known non-article boilerplate."""
        if content is None:
            return False
        return content in self.BOILERPLATE_CONTENTS

    def __init__(self, semaphore: asyncio.Semaphore) -> None:
        """Initialize with a shared semaphore to limit concurrent enrich requests."""
        self._semaphore = semaphore
        self._user_agent = settings.user_agent
        self._newspaper_config = newspaper.Config()

    @abstractmethod
    async def run_fetch(self, executed_at: datetime) -> list[BronzeNewsModel]:
        """Fetch raw RSS feed and map to BronzeNewsModel entities without enrichment."""
        pass

    async def run_enrich(self, items: list[BronzeNewsModel]) -> list[BronzeNewsModel]:
        """
        Enrich targeted items with full article content in parallel.

        HTTP and parsing errors are isolated into top-level diagnostics,
        allowing other successful items to proceed.
        """
        if not items:
            logger.info(
                "Plugin run_enrich skipped | source: %s, reason: no items",
                self.source,
            )
            return []

        tasks = [self._enrich(item.entry_url) for item in items]
        enrichments = await asyncio.gather(*tasks)

        unique_candidates: dict[str, BronzeNewsModel] = {}

        for item, enriched in zip(items, enrichments):
            content = enriched.content
            status_code = enriched.status_code
            error_message = enriched.error_message

            if content is not None:
                content = content.strip() or None

            if self._is_boilerplate_content(content):
                content = None
                if error_message is None:
                    error_message = "Content extraction failed::boilerplate content"

            if status_code == 200 and content:
                status = "success"
            else:
                status = "failed"
                if error_message is None:
                    error_message = (
                        f"HTTP status not OK::status_code={status_code}"
                        if status_code != 200
                        else "Content unavailable::empty content"
                    )

            target_url = enriched.canonical_url or item.entry_url
            news_id = self._make_id(target_url)

            # Dump enriched schema properties directly and overlay normalized enrichment fields and diagnostics.
            update_fields = enriched.model_dump(exclude={"status_code", "error_message"})
            update_fields.update(
                {
                    "news_id": news_id,
                    "content": content,
                    "status": status,
                    "status_code": status_code,
                    "error_message": error_message,
                }
            )

            new_item = item.model_copy(update=update_fields)

            existing_item = unique_candidates.get(news_id)
            if existing_item is None or (existing_item.status != "success" and new_item.status == "success"):
                unique_candidates[news_id] = new_item

        deduplicated_items = list(unique_candidates.values())
        succeeded_count = sum(1 for item in deduplicated_items if item.status == "success")
        failed_count = sum(1 for item in deduplicated_items if item.status != "success")
        logger.info(
            "Plugin run_enrich completed | source: %s, total_unique: %d, succeeded: %d, failed_count: %d",
            self.source,
            len(deduplicated_items),
            succeeded_count,
            failed_count,
        )
        return deduplicated_items

    async def _fetch_feed(self) -> feedparser.FeedParserDict:
        """Fetch raw RSS feed using feedparser and validate HTTP status."""
        feed = await asyncio.to_thread(feedparser.parse, self.RSS_URL, agent=self._user_agent)

        status = feed.get("status")
        if status is None:
            raise RuntimeError("RSS fetch failed::missing status_code")

        if status != 200:
            raise RuntimeError(f"RSS fetch failed::status_code={status}")

        return feed

    async def _enrich(self, url: str) -> SourceEnrichedArticleSchema:
        """
        Fetch and parse full article content for a single URL.

        Use httpx for async I/O to get status_code and HTML,
        then use newspaper4k for CPU-bound text extraction.
        Return a SourceEnrichedArticleSchema with extracted article fields and diagnostics.
        Limit concurrent requests across all sources using the shared semaphore.
        """
        status_code, html, error_message = await self._fetch_html(url)

        if status_code == 200 and html:
            try:
                parsed = await asyncio.to_thread(self._parse_article_html, url, html)
                return parsed.model_copy(update={"status_code": status_code, "error_message": error_message})
            except Exception as e:
                error_message = f"Parsing failed::{type(e).__name__}::{e}"

        return SourceEnrichedArticleSchema(
            status_code=status_code,
            error_message=error_message,
        )

    @_retry
    async def _fetch_html(self, url: str) -> tuple[int | None, str | None, str | None]:
        """Fetch HTML content asynchronously with transient failure retries."""
        try:
            # Jitter each attempt to reduce bursty requests against article hosts.
            await asyncio.sleep(random.uniform(0.1, 0.5))
            async with self._semaphore:
                async with httpx.AsyncClient(follow_redirects=True) as client:
                    response = await client.get(url, headers={"User-Agent": self._user_agent}, timeout=10.0)
                    return response.status_code, response.text, None
        except Exception as e:
            # Network error or unexpected exception before receiving an HTTP response.
            return None, None, f"Network error::{type(e).__name__}::{e}"

    def _make_id(self, url: str) -> str:
        """Generate a deterministic UUID v5 from a normalized URL."""
        parts = urlsplit(url.strip())
        normalized_url = urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path, parts.query, ""))
        return str(uuid.uuid5(_NAMESPACE_UUID, normalized_url))

    def _is_valid_rss_entry(self, entry_data: object, seen_unknowns: set[str]) -> bool:
        """Return True for mapping RSS entries and warn once for unknown fields."""
        if not isinstance(entry_data, Mapping):
            logger.warning(
                "Plugin _is_valid_rss_entry failed | source: %s, reason: %s, entry: %s",
                self.source,
                f"TypeError::expected mapping entry, got {type(entry_data).__name__}",
                str(entry_data),
            )
            return False

        unknown_fields = entry_data.keys() - self.RSS_ENTRY_KNOWN_FIELDS
        new_unknowns = unknown_fields - seen_unknowns
        if new_unknowns:
            logger.warning(
                "Plugin _is_valid_rss_entry [unknown_fields] detected | source: %s, fields: %s",
                self.source,
                sorted(new_unknowns),
            )
            seen_unknowns.update(new_unknowns)

        return True

    def _parse_article_html(self, url: str, html: str) -> SourceEnrichedArticleSchema:
        """Extract text and metadata from raw HTML synchronously using newspaper4k."""
        article = newspaper.Article(url, config=self._newspaper_config)
        article.html = html
        article.parse()

        authors = getattr(article, "authors", None)
        canonical_url = getattr(article, "canonical_link", None) or None
        image_url = getattr(article, "top_image", None) or None
        language = getattr(article, "meta_lang", None) or None
        content = getattr(article, "text", None) or None

        return SourceEnrichedArticleSchema(
            authors="|".join(authors) if authors else None,
            canonical_url=canonical_url,
            image_url=image_url,
            language=language,
            content=content,
        )
