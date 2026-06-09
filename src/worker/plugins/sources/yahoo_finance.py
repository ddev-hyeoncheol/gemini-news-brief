from collections.abc import Mapping
from datetime import datetime, timezone

from src.core.logger import get_logger
from src.models.entities.bronze_news import BronzeNewsModel
from src.models.schemas.sources.yahoo_finance import YahooFinanceEntrySchema
from src.worker.plugins.source import SourcePlugin

logger = get_logger(__name__)


class YahooFinanceSource(SourcePlugin):
    """News source for Yahoo Finance RSS feed."""

    @property
    def source(self) -> str:
        return "yahoo_finance"

    @property
    def RSS_URL(self) -> str:
        return "https://finance.yahoo.com/rss/"

    @property
    def RSS_ENTRY_STORAGE_FIELDS(self) -> set[str]:
        return {"title", "link", "published_parsed", "media_content"}

    @property
    def RSS_ENTRY_METADATA_FIELDS(self) -> set[str]:
        return {"source", "id"}

    @property
    def RSS_ENTRY_IGNORED_FIELDS(self) -> set[str]:
        return {"title_detail", "links", "published", "guidislink", "media_credit", "credit"}

    @property
    def BOILERPLATE_CONTENTS(self) -> set[str]:
        return {
            "Sign in to access your portfolio\n\nSign in",
        }

    async def run_fetch(self, executed_at: datetime) -> list[BronzeNewsModel]:
        """Fetch raw RSS feed and map to BronzeNewsModel entities without enrichment."""

        raw_feed = await self._fetch_feed()
        entries_data = raw_feed.get("entries") or []

        results: list[BronzeNewsModel] = []
        seen_unknowns: set[str] = set()

        for entry_data in entries_data:
            try:
                if isinstance(entry_data, Mapping):
                    self._warn_unknown_fields(entry_data=entry_data, seen_unknowns=seen_unknowns)

                entry = YahooFinanceEntrySchema.model_validate(entry_data)
            except Exception:
                continue

            entry_id = self._make_id(entry.link)

            published_at = self._parse_published_at(entry=entry)
            if published_at is None:
                continue

            thumbnail_url = None
            if entry.media_content:
                first_media = entry.media_content[0]
                if first_media.url:
                    thumbnail_url = first_media.url

            metadata_payload = entry.model_dump(exclude=self.RSS_ENTRY_STORAGE_FIELDS, mode="json")

            results.append(
                BronzeNewsModel(
                    executed_at=executed_at,
                    entry_id=entry_id,
                    news_id=entry_id,
                    source=self.source,
                    title=entry.title,
                    entry_url=entry.link,
                    published_at=published_at,
                    thumbnail_url=thumbnail_url,
                    metadata=metadata_payload,
                )
            )

        success_count = len(results)
        total_count = len(entries_data)

        logger.info(
            "SourcePlugin fetch completed | source: %s, count: %d, total_count: %d, skipped_count: %d",
            self.source,
            success_count,
            total_count,
            total_count - success_count,
        )
        return results

    def _parse_published_at(self, entry: YahooFinanceEntrySchema) -> datetime | None:
        """Return the RSS publication timestamp as a UTC datetime."""
        published_parsed = entry.published_parsed
        if not isinstance(published_parsed, (list, tuple)):
            return None
        try:
            return datetime(*published_parsed[:6], tzinfo=timezone.utc)
        except Exception:
            return None
