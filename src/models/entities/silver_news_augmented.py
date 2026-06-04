from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class SilverNewsAugmentedMarketEntityModel(BaseModel):
    """Market entity stored in the Silver news augmented table."""

    entity_type: str = Field(description="AI-classified market entity type")
    name: str | None = Field(default=None, description="AI-identified market entity name")
    symbol: str | None = Field(default=None, description="AI-identified ticker or market symbol")


class SilverNewsAugmentedModel(BaseModel):
    """
    Entity model representing AI-augmented data for Silver tier news.
    Contains LLM-generated insights, summaries, and processing status.
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
    news_id: str = Field(description="Stable article URL-based news item identifier")

    # LLM Metadata
    model_provider: str = Field(description="LLM provider name")
    model_name: str = Field(description="LLM model name")
    analysis_version: str = Field(description="AI analysis contract version")

    # AI Classification
    ai_category: str | None = Field(default=None, description="AI-classified economic news category")
    ai_format: str | None = Field(default=None, description="AI-classified news item format")
    ai_sentiment: str | None = Field(default=None, description="AI-classified news item sentiment")

    # AI Market Entities
    ai_market_entities: list[SilverNewsAugmentedMarketEntityModel] = Field(
        default_factory=list,
        description="AI-extracted market entities",
    )

    # AI Cleanup Outputs
    ai_authors: list[str] = Field(default_factory=list, description="AI-cleaned author names")
    ai_content: str | None = Field(default=None, description="AI-cleaned article body text")

    # AI Korean Outputs
    ai_title_ko: str | None = Field(default=None, description="AI-translated news item title in Korean")
    ai_summary_ko: str | None = Field(default=None, description="AI-generated news item summary in Korean")
    ai_summary_bullets_ko: list[str] = Field(
        default_factory=list, description="AI-generated bullet point news item summary in Korean"
    )
    ai_content_ko: str | None = Field(default=None, description="AI-translated article body text in Korean")

    # Processing Diagnostics
    batch_id: str = Field(description="Deterministic LLM chunk batch identifier")
    status: Literal["success", "failed"] = Field(description="AI augmentation processing status")
    error_message: str | None = Field(default=None, description="AI augmentation error message")
