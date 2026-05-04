from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, Field

from src.models.entities.news import BronzeNewsModel


class IngestRequest(BaseModel):
    executed_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc),
        description="Execution time (UTC). Defaults to current time if not provided.",
    )


class IngestPhaseResultBase(BaseModel):
    """Base DTO for intermediate pipeline phases sharing common fields."""

    source: str = Field(
        description="News source name.",
    )
    item_count: int = Field(
        default=0,
        description="Number of items resulting from this phase.",
    )
    items: list[BronzeNewsModel] = Field(
        default_factory=list,
        description="List of processed news items.",
    )
    started_at: datetime = Field(
        description="Timestamp when the phase started (UTC).",
    )
    completed_at: datetime = Field(
        description="Timestamp when the phase finished (UTC).",
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if the phase failed.",
    )


class IngestFetchResult(IngestPhaseResultBase):
    status: Literal["success", "failed"] = Field(
        description="Fetch status.",
    )


class IngestLookupResult(IngestPhaseResultBase):
    status: Literal["success", "failed"] = Field(
        description="Lookup status.",
    )


class IngestEnrichResult(IngestPhaseResultBase):
    status: Literal["success", "partial", "failed"] = Field(
        description="Enrichment status.",
    )


class IngestLoadResult(IngestPhaseResultBase):
    status: Literal["success", "partial", "failed"] = Field(
        description="Load status.",
    )


class IngestSourceResult(BaseModel):
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
        description="Number of successfully loaded or updated news items.",
    )
    started_at: datetime | None = Field(
        default=None,
        description="Timestamp when pipeline started for this source (UTC).",
    )
    completed_at: datetime | None = Field(
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
    executed_at: datetime = Field(
        description="Execution time passed in the request (UTC).",
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
        description="Total number of successfully loaded or updated news items across all sources.",
    )
    sources: list[IngestSourceResult] = Field(
        default_factory=list,
        description="Per-source ingestion results.",
    )
