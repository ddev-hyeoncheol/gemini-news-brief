from datetime import datetime, timezone
from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field, AwareDatetime

from src.models.entities.bronze_news import BronzeNewsModel


def _floor_to_10min(dt: datetime) -> datetime:
    """Floor a datetime to the nearest 10-minute boundary."""
    floored = dt.replace(second=0, microsecond=0, minute=(dt.minute // 10) * 10)
    return floored


class IngestTarget(str, Enum):
    """Supported ingestion pipeline targets."""

    NEWS = "news"


class IngestRequest(BaseModel):
    """Request payload to trigger the ingestion pipeline."""

    executed_at: AwareDatetime = Field(
        default_factory=lambda: _floor_to_10min(datetime.now(tz=timezone.utc)),
        description="Batch execution time (UTC), floored to 10-minute intervals. Defaults to current time if not provided.",
    )


class IngestPhaseResultBase(BaseModel):
    """Base DTO for intermediate pipeline phases sharing common fields."""

    source: str = Field(
        description="News source name.",
    )
    item_count: int = Field(
        default=0,
        description="Phase-specific news item count.",
    )
    items: list[BronzeNewsModel] = Field(
        default_factory=list,
        description="List of news items produced by this phase.",
    )
    started_at: AwareDatetime = Field(
        description="Timestamp when the phase started (UTC).",
    )
    completed_at: AwareDatetime = Field(
        description="Timestamp when the phase finished (UTC).",
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if the phase failed.",
    )


class IngestFetchResult(IngestPhaseResultBase):
    """Result DTO for the feed fetch phase."""

    status: Literal["success", "failed"] = Field(
        description="Fetch status.",
    )


class IngestLookupResult(IngestPhaseResultBase):
    """Result DTO for the storage lookup phase."""

    status: Literal["success", "failed"] = Field(
        description="Lookup status.",
    )


class IngestEnrichResult(IngestPhaseResultBase):
    """Result DTO for the content enrichment phase."""

    status: Literal["success", "partial", "failed"] = Field(
        description="Enrichment status.",
    )


class IngestLoadResult(IngestPhaseResultBase):
    """Result DTO for the storage load phase."""

    status: Literal["success", "failed"] = Field(
        description="Load status.",
    )


class IngestSourceResult(BaseModel):
    """Aggregated ingestion result for a single news source."""

    source: str = Field(
        description="News source name.",
    )
    status: Literal["success", "partial", "failed"] = Field(
        description="Overall pipeline status for this source.",
    )
    fetched_count: int = Field(
        default=0,
        description="Total number of news items fetched from the source feed.",
    )
    lookup_count: int = Field(
        default=0,
        description="Number of new or updated news items targeted for scraping after lookup.",
    )
    enriched_count: int = Field(
        default=0,
        description="Number of successfully enriched news items.",
    )
    loaded_count: int = Field(
        default=0,
        description="Number of news items loaded into storage.",
    )
    started_at: AwareDatetime | None = Field(
        default=None,
        description="Timestamp when pipeline started for this source (UTC).",
    )
    completed_at: AwareDatetime | None = Field(
        default=None,
        description="Timestamp when pipeline finished for this source (UTC).",
    )
    failed_phase: Literal["fetch", "lookup", "enrich", "load"] | None = Field(
        default=None,
        description="The pipeline phase where the failure occurred.",
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if the pipeline failed for this source.",
    )


class IngestResponse(BaseModel):
    """Response payload for the ingestion pipeline execution."""

    executed_at: AwareDatetime = Field(
        description="Batch execution time passed in the request (UTC).",
    )
    status: Literal["success", "partial", "failed"] = Field(
        description="Overall ingestion status.",
    )
    fetched_count: int = Field(
        default=0,
        description="Total number of news items fetched from the source feeds across all sources.",
    )
    lookup_count: int = Field(
        default=0,
        description="Total number of new or updated news items targeted for scraping across all sources.",
    )
    enriched_count: int = Field(
        default=0,
        description="Total number of successfully enriched news items across all sources.",
    )
    loaded_count: int = Field(
        default=0,
        description="Total number of news items loaded into storage across all sources.",
    )
    sources: list[IngestSourceResult] = Field(
        default_factory=list,
        description="Per-source ingestion results.",
    )
