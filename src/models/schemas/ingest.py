from datetime import datetime, timezone

from typing import Literal
from pydantic import BaseModel, Field

from src.models.entities.news import BronzeNewsModel


class IngestRequest(BaseModel):
    executed_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc),
        description="Execution time (UTC). Defaults to current time if not provided.",
    )
    window: int = Field(
        default=10,
        ge=1,
        description="Time window in minutes. Only news published within this range will be collected.",
    )


class IngestCollectParseResult(BaseModel):
    target_count: int = Field(
        description="Number of candidates found within the time window."
    )
    items: list[BronzeNewsModel] = Field(
        default_factory=list, description="List of successfully parsed news items."
    )


class IngestCollectResult(BaseModel):
    source: str = Field(description="News source name.")
    status: Literal["success", "partial", "failed"] = Field(
        description="Collection status for this source."
    )
    items: list[BronzeNewsModel] = Field(
        default_factory=list, description="List of collected news items."
    )
    target_count: int = Field(
        default=0,
        description="Total number of items discovered within the time window.",
    )
    collected_count: int = Field(
        default=0, description="Number of successfully collected news items."
    )
    started_at: datetime = Field(description="Timestamp when collection started (UTC).")
    collected_at: datetime = Field(
        description="Timestamp when collection finished (UTC)."
    )
    error_message: str | None = Field(
        default=None, description="Error message if collection failed."
    )


class IngestLoadResult(BaseModel):
    source: str = Field(description="News source name.")
    status: Literal["success", "partial", "failed"] = Field(
        description="Load status for this source."
    )
    target_count: int = Field(
        default=0, description="Number of collected items attempted to be loaded."
    )
    loaded_count: int = Field(
        default=0,
        description="Number of successfully loaded news items (BigQuery dedup is handled at query time).",
    )
    started_at: datetime = Field(description="Timestamp when load started (UTC).")
    loaded_at: datetime = Field(description="Timestamp when load finished (UTC).")
    error_message: str | None = Field(
        default=None,
        description="Error message if load failed.",
    )


class IngestSourceResult(BaseModel):
    source: str = Field(description="News source name.")
    status: Literal["success", "partial", "failed"] = Field(
        description="Overall pipeline status for this source."
    )
    target_count: int = Field(
        default=0,
        description="Total number of items discovered within the time window.",
    )
    collected_count: int = Field(
        default=0, description="Number of items successfully collected."
    )
    loaded_count: int = Field(
        default=0, description="Number of items successfully loaded."
    )
    collect_started_at: datetime | None = Field(
        default=None, description="Timestamp when collection started (UTC)."
    )
    collected_at: datetime | None = Field(
        default=None, description="Timestamp when collection finished (UTC)."
    )
    load_started_at: datetime | None = Field(
        default=None, description="Timestamp when load started (UTC)."
    )
    loaded_at: datetime | None = Field(
        default=None, description="Timestamp when load finished (UTC)."
    )
    failed_phase: Literal["collect", "load"] | None = Field(
        default=None, description="The pipeline phase where the failure occurred."
    )
    error_message: str | None = Field(
        default=None, description="Error message if collection or load failed."
    )


class IngestResponse(BaseModel):
    executed_at: datetime = Field(
        description="Execution time passed in the request (UTC)."
    )
    status: Literal["success", "partial", "failed"] = Field(
        description="Overall ingestion status."
    )
    target_count: int = Field(
        description="Total number of news items discovered across all sources within the time window."
    )
    collected_count: int = Field(
        description="Total number of news items collected across all sources."
    )
    loaded_count: int = Field(
        description="Total number of news items loaded to BigQuery."
    )
    sources: list[IngestSourceResult] = Field(
        description="Per-source ingestion results."
    )
