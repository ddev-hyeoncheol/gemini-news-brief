from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import AwareDatetime, BaseModel, Field

BatchStatus = Literal["success", "partial", "failed"]
BatchPhase = Literal["fetch", "entry_lookup", "enrich", "news_lookup", "load"]


class BatchLayer(str, Enum):
    """Supported batch database layers."""

    BRONZE = "bronze"


class BatchTarget(str, Enum):
    """Supported batch logic targets."""

    NEWS = "news"


# Supported layer/target combinations.
VALID_BATCH_COMBINATIONS: set[tuple[BatchLayer, BatchTarget]] = {
    (BatchLayer.BRONZE, BatchTarget.NEWS),
}


class BatchRequest(BaseModel):
    """Request payload to trigger a batch execution."""

    executed_at: AwareDatetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc),
        description="Requested batch execution time. Defaults to current UTC time if not provided.",
    )


class BatchSourceResult(BaseModel):
    """Response payload for a Bronze news source execution."""

    source: str = Field(
        description="News source name.",
    )
    executed_at: AwareDatetime = Field(
        description="Normalized batch execution time (UTC).",
    )
    status: BatchStatus = Field(
        description="Status of this source execution.",
    )
    count: int = Field(
        default=0,
        description="Number of news items loaded by this source execution.",
    )
    started_at: AwareDatetime | None = Field(
        default=None,
        description="Timestamp when this source execution started (UTC).",
    )
    completed_at: AwareDatetime | None = Field(
        default=None,
        description="Timestamp when this source execution finished (UTC).",
    )
    elapsed_seconds: float | None = Field(
        default=None,
        description="Duration of this source execution in seconds.",
    )
    failed_phase: BatchPhase | None = Field(
        default=None,
        description="Source execution phase where a phase-level failure occurred.",
    )
    error_message: str | None = Field(
        default=None,
        description="Phase-level error message for this source execution.",
    )


class BatchResponse(BaseModel):
    """Response payload for a batch task execution."""

    layer: BatchLayer = Field(
        description="Database layer targeted by this batch task execution.",
    )
    target: BatchTarget = Field(
        description="Logic target of this batch task execution.",
    )
    executed_at: AwareDatetime = Field(
        description="Normalized batch execution time (UTC).",
    )
    status: BatchStatus = Field(
        description="Status of this batch task execution.",
    )
    count: int = Field(
        default=0,
        description="Number of records loaded by this batch task execution.",
    )
    started_at: AwareDatetime | None = Field(
        default=None,
        description="Timestamp when this batch task execution started (UTC).",
    )
    completed_at: AwareDatetime | None = Field(
        default=None,
        description="Timestamp when this batch task execution finished (UTC).",
    )
    elapsed_seconds: float | None = Field(
        default=None,
        description="Duration of this batch task execution in seconds.",
    )
    failed_phase: BatchPhase | None = Field(
        default=None,
        description="Batch task execution phase where a phase-level failure occurred.",
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if this batch task execution failed.",
    )
    details: list[BatchSourceResult] | None = Field(
        default=None,
        description="Bronze news source execution results for this batch task execution, when available.",
    )


class BatchPipelineResponse(BaseModel):
    """Response payload for the full batch pipeline execution."""

    executed_at: AwareDatetime = Field(
        description="Normalized batch execution time (UTC).",
    )
    status: BatchStatus = Field(
        description="Status of this batch pipeline execution.",
    )
    started_at: AwareDatetime | None = Field(
        default=None,
        description="Timestamp when this batch pipeline execution started (UTC).",
    )
    completed_at: AwareDatetime | None = Field(
        default=None,
        description="Timestamp when this batch pipeline execution finished (UTC).",
    )
    elapsed_seconds: float | None = Field(
        default=None,
        description="Duration of this batch pipeline execution in seconds.",
    )
    tasks: list[BatchResponse] = Field(
        default_factory=list,
        description="Batch task execution results produced by this batch pipeline execution.",
    )
