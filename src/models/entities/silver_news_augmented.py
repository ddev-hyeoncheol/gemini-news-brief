from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, AwareDatetime


class SilverNewsAugmentedModel(BaseModel):
    """
    Entity model representing AI-augmented data for Silver tier news.
    Contains LLM-generated insights, summaries, and processing metrics.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        frozen=True,
        # Silently ignore extra fields (e.g. 'loaded_at') returned by BigQuery queries.
        extra="ignore",
    )

    # 1. Partition Key
    executed_at: AwareDatetime = Field(description="Executed at")

    # 2. Identification Keys
    news_id: str = Field(description="News ID (Hash)")

    # 3. Clustering Keys
    model: str = Field(description="LLM model name")
    version: str = Field(description="LLM model version")

    # 4. AI Augmented Fields
    ai_sector: str | None = Field(
        default=None, description="AI-determined economic sector"
    )
    ai_format: str | None = Field(
        default=None, description="AI-determined article format"
    )
    ai_sentiment: str | None = Field(
        default=None, description="AI-determined sentiment"
    )
    ai_title: str | None = Field(
        default=None, description="AI-translated title in Korean"
    )
    ai_author: list[str] = Field(
        default_factory=list, description="AI-determined authors"
    )
    ai_summary: str | None = Field(
        default=None, description="AI-generated summary in Korean"
    )
    ai_content_clean: str | None = Field(default=None, description="AI-cleaned content")
    # 'loaded_at' is excluded from the model. StoreBase.execute_load_json injects it at load time.

    # 5. Pipeline Tracking Fields
    batch_id: str = Field(description="Batch ID (Hash of news IDs in the batch)")
    status: Literal["success", "failed"] = Field(description="Processing status")
    error_message: str | None = Field(default=None, description="Error message")
