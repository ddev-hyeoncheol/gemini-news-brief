from typing import Any, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class BronzeNewsModel(BaseModel):
    """
    Entity model representing the Bronze tier news data.
    Contains raw news items collected directly from external sources.
    """

    model_config = ConfigDict(
        # 'loaded_at' is excluded from the model. BigQueryProvider.execute_load_json injects it at load time.
        # extra="ignore" accepts queried BigQuery rows that include the injected column.
        extra="ignore",
        frozen=True,
        str_strip_whitespace=True,
    )

    # Identity & Partitioning
    executed_at: AwareDatetime = Field(description="Batch execution timestamp")
    entry_id: str = Field(description="Stable RSS entry identifier")
    news_id: str = Field(description="Stable article URL-based news item identifier")
    source: str = Field(description="RSS feed provider identifier")

    # RSS Fetch (feedparser)
    title: str = Field(description="RSS-provided news item title")
    entry_url: str = Field(description="RSS-provided news item URL")
    published_at: AwareDatetime = Field(description="RSS-provided publication timestamp")
    updated_at: AwareDatetime | None = Field(default=None, description="RSS-provided update timestamp")
    thumbnail_url: str | None = Field(default=None, description="RSS-provided thumbnail image URL")

    # HTML Enrich (newspaper4k)
    authors: str | None = Field(default=None, description="HTML-extracted pipe-delimited author names")
    canonical_url: str | None = Field(default=None, description="HTML-declared canonical URL")
    image_url: str | None = Field(default=None, description="HTML-extracted representative image URL")
    language: str | None = Field(default=None, description="HTML-declared language code")
    content: str | None = Field(default=None, description="HTML-extracted article body text")

    # Processing Diagnostics
    status: Literal["success", "failed"] | None = Field(default=None, description="Bronze item processing status")
    status_code: int | None = Field(default=None, description="Bronze item HTTP status code")
    error_message: str | None = Field(default=None, description="Bronze item error message")

    # Source Metadata
    metadata: dict[str, Any] | None = Field(default=None, description="Source-specific RSS metadata")
