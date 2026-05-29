from typing import Any, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class BronzeNewsModel(BaseModel):
    """
    Entity model representing the Bronze tier news data.
    Contains raw news items collected directly from external sources.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        frozen=True,
        # Silently ignore extra fields (e.g. 'loaded_at') returned by BigQuery queries.
        extra="ignore",
    )

    # Identity & Partitioning
    executed_at: AwareDatetime = Field(description="Batch execution timestamp")
    entry_id: str = Field(description="Stable RSS entry identifier")
    news_id: str = Field(description="Stable news item identifier")
    source: str = Field(description="RSS feed provider identifier")

    # RSS fetch (feedparser)
    title: str = Field(description="RSS-provided news item title")
    entry_url: str = Field(description="RSS-provided news item URL")
    published_at: AwareDatetime = Field(description="RSS-provided publication timestamp")
    updated_at: AwareDatetime | None = Field(default=None, description="RSS-provided update timestamp")
    original_source_name: str | None = Field(default=None, description="RSS-provided original publisher name")
    original_source_url: str | None = Field(default=None, description="RSS-provided original publisher URL")
    thumbnail_url: str | None = Field(default=None, description="RSS-provided thumbnail image URL")

    # HTML enrich (newspaper4k)
    authors: str | None = Field(default=None, description="HTML-extracted author names")
    canonical_url: str | None = Field(default=None, description="HTML-declared canonical URL")
    image_url: str | None = Field(default=None, description="HTML-extracted representative image URL")
    language: str | None = Field(default=None, description="HTML-declared language code")
    content: str | None = Field(default=None, description="HTML-extracted article body text")

    # Processing diagnostics
    status: Literal["success", "failed"] | None = Field(default=None, description="Bronze item ingestion status")
    status_code: int | None = Field(
        default=None,
        description="Bronze item ingestion HTTP status code; 0 indicates a network error",
    )
    error_message: str | None = Field(default=None, description="Bronze item ingestion error message")

    # Source metadata
    metadata: dict[str, Any] | None = Field(default=None, description="Source-specific RSS metadata")
