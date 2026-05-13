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


class RefineRequest(BaseModel):
    """Request payload to trigger the refinement pipeline."""

    executed_at: AwareDatetime = Field(
        description="Execution time passed in the request (UTC).",
    )
    target_table: str = Field(
        description="Target BigQuery table name to process.",
    )


class RefinePhaseResultBase(BaseModel, Generic[T]):
    """Base DTO for intermediate pipeline phases sharing common fields."""

    target_table: str = Field(
        description="Target BigQuery table name.",
    )
    item_count: int = Field(
        default=0,
        description="Number of items resulting from this phase.",
    )
    items: list[T] = Field(
        default_factory=list,
        description="List of processed news items.",
    )
    started_at: AwareDatetime = Field(
        description="Timestamp when the phase started (UTC)."
    )
    completed_at: AwareDatetime = Field(
        description="Timestamp when the phase finished (UTC)."
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if the phase failed.",
    )


class RefineExtractResult(RefinePhaseResultBase[T], Generic[T]):
    status: Literal["success", "failed"] = Field(
        description="Extract status.",
    )


class RefineTransformResult(RefinePhaseResultBase[T], Generic[T]):
    status: Literal["success", "partial", "failed"] = Field(
        description="Transform status.",
    )


class RefineLoadResult(RefinePhaseResultBase[T], Generic[T]):
    status: Literal["success", "failed"] = Field(
        description="Load status.",
    )


class RefineResponse(BaseModel):
    """Response payload for the refinement pipeline execution."""

    executed_at: AwareDatetime = Field(
        description="Execution time passed in the request (UTC).",
    )
    target_table: str = Field(
        description="Target BigQuery table name.",
    )
    status: Literal["success", "partial", "failed"] = Field(
        description="Overall pipeline status for this target.",
    )
    extracted_count: int = Field(
        default=0,
        description="Total number of news items extracted from the source tier.",
    )
    transformed_count: int = Field(
        default=0,
        description="Number of successfully transformed news items.",
    )
    loaded_count: int = Field(
        default=0,
        description="Number of successfully loaded news items.",
    )
    started_at: AwareDatetime | None = Field(
        default=None,
        description="Timestamp when pipeline started for this target (UTC).",
    )
    completed_at: AwareDatetime | None = Field(
        default=None,
        description="Timestamp when pipeline finished for this target (UTC).",
    )
    failed_phase: Literal["extract", "transform", "load"] | None = Field(
        default=None,
        description="The pipeline phase where the failure occurred.",
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if the pipeline failed for this target.",
    )
