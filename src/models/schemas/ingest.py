from datetime import datetime, timezone

from typing import Literal
from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    scheduled_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc),
        description="Scheduled execution time (UTC). Defaults to current time if not provided.",
    )
    window: int = Field(
        default=10,
        ge=1,
        description="Time window in minutes. Only news published within this range will be collected.",
    )


class IngestSourceResult(BaseModel):
    name: str = Field(description="News source name.")
    status: Literal["success", "failed"] = Field(
        description="Collection status for this source."
    )
    total_count: int = Field(
        description="Total number of news items fetched from this source."
    )
    saved_count: int = Field(
        description="Number of news items saved to BigQuery (duplicates excluded)."
    )
    started_at: datetime = Field(
        description="Timestamp when collection for this source started (UTC)."
    )
    completed_at: datetime = Field(
        description="Timestamp when collection for this source completed (UTC)."
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if collection failed for this source; null if successful.",
    )


class IngestResponse(BaseModel):
    scheduled_at: datetime = Field(
        description="Scheduled execution time passed in the request (UTC)."
    )
    status: Literal["success", "partial", "failed"] = Field(
        description="Overall collection status."
    )
    total_count: int = Field(
        description="Total number of news items fetched across all sources."
    )
    saved_count: int = Field(
        description="Total number of news items saved to BigQuery."
    )
    sources: list[IngestSourceResult] = Field(
        description="Per-source collection results."
    )
