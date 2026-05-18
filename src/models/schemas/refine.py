from datetime import datetime, timezone
from enum import Enum
from typing import Literal, Generic, TypeVar
from pydantic import BaseModel, Field, AwareDatetime

from src.models.entities.bronze_news import BronzeNewsModel
from src.models.entities.silver_news import SilverNewsModel
from src.models.entities.silver_news_augmented import SilverNewsAugmentedModel

T = TypeVar(
    "T",
    BronzeNewsModel,
    SilverNewsModel,
    SilverNewsAugmentedModel,
)


def _floor_to_10min(dt: datetime) -> datetime:
    """Floor a datetime to the nearest 10-minute boundary."""
    floored = dt.replace(second=0, microsecond=0, minute=(dt.minute // 10) * 10)
    return floored


class RefineTarget(str, Enum):
    """Supported refinement pipeline targets."""

    NEWS = "news"
    NEWS_AUGMENTED = "news-augmented"


class RefineRequest(BaseModel):
    """Request payload to trigger the refinement pipeline."""

    executed_at: AwareDatetime = Field(
        default_factory=lambda: _floor_to_10min(datetime.now(tz=timezone.utc)),
        description="Batch execution time (UTC), floored to 10-minute intervals. Defaults to current time if not provided.",
    )


class RefinePhaseResultBase(BaseModel, Generic[T]):
    """Base DTO for intermediate pipeline phases sharing common fields."""

    item_count: int = Field(
        default=0,
        description="Phase-specific record count.",
    )
    items: list[T] = Field(
        default_factory=list,
        description="List of records produced by this phase.",
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


class RefineExtractResult(RefinePhaseResultBase[T], Generic[T]):
    """Result DTO for the source tier extraction phase."""

    status: Literal["success", "failed"] = Field(
        description="Extract status.",
    )


class RefineTransformResult(RefinePhaseResultBase[T], Generic[T]):
    """Result DTO for the transformation phase."""

    status: Literal["success", "partial", "failed"] = Field(
        description="Transform status.",
    )


class RefineLoadResult(RefinePhaseResultBase[T], Generic[T]):
    """Result DTO for the storage load phase."""

    status: Literal["success", "failed"] = Field(
        description="Load status.",
    )


class RefineResponse(BaseModel):
    """Response payload for the refinement pipeline execution."""

    executed_at: AwareDatetime = Field(
        description="Batch execution time passed in the request (UTC).",
    )
    status: Literal["success", "partial", "failed"] = Field(
        description="Overall refinement pipeline status.",
    )
    extracted_count: int = Field(
        default=0,
        description="Total number of records extracted from the source tier.",
    )
    transformed_count: int = Field(
        default=0,
        description="Number of records successfully transformed.",
    )
    loaded_count: int = Field(
        default=0,
        description="Number of records loaded into storage.",
    )
    started_at: AwareDatetime | None = Field(
        default=None,
        description="Timestamp when the refinement pipeline started (UTC).",
    )
    completed_at: AwareDatetime | None = Field(
        default=None,
        description="Timestamp when the refinement pipeline finished (UTC).",
    )
    failed_phase: Literal["extract", "transform", "load"] | None = Field(
        default=None,
        description="The pipeline phase where the failure occurred.",
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if the refinement pipeline failed.",
    )
