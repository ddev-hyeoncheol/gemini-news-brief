from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class SilverNewsAugmentedModel(BaseModel):
    """
    Entity model representing AI-augmented data for Silver tier news.
    Contains LLM-generated insights, summaries, and processing status.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        frozen=True,
        # Silently ignore extra fields (e.g. 'loaded_at') returned by BigQuery queries.
        extra="ignore",
    )

    # 1. Partition Key
    executed_at: AwareDatetime = Field(description="Batch execution timestamp")

    # 2. Identification Keys
    news_id: str = Field(description="Stable unique news item identifier")

    # 3. Clustering Keys
    model: str = Field(description="LLM model name")
    version: str = Field(description="LLM analysis schema version")

    # 4. AI Augmented Fields
    ai_sector: str | None = Field(
        default=None, description="AI-classified economic sector"
    )
    ai_format: str | None = Field(
        default=None, description="AI-classified news item format"
    )
    ai_sentiment: str | None = Field(
        default=None, description="AI-classified news item sentiment"
    )
    ai_title: str | None = Field(
        default=None, description="Korean translation of the news item title"
    )
    ai_author: list[str] = Field(
        default_factory=list, description="Normalized news item author names"
    )
    ai_summary: str | None = Field(
        default=None, description="Korean summary of the news item"
    )
    ai_content_clean: str | None = Field(
        default=None, description="News item body text with boilerplate removed"
    )
    # 'loaded_at' is excluded from the model. StoreBase.execute_load_json injects it at load time.

    # 5. Processing Status Fields
    batch_id: str = Field(description="LLM request batch identifier")
    status: Literal["success", "failed"] = Field(
        description="AI augmentation processing status"
    )
    error_message: str | None = Field(
        default=None, description="AI augmentation error message"
    )
