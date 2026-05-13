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
    ai_category: str | None = Field(default=None, description="AI-determined category")
    ai_author: str | None = Field(default=None, description="AI-determined author")
    ai_content_clean: str | None = Field(default=None, description="AI-cleaned content")
    ai_summary: str | None = Field(default=None, description="AI-generated summary")
    ai_sentiment: str | None = Field(
        default=None, description="AI-determined sentiment"
    )
    # 'loaded_at' is excluded from the model. StoreBase.execute_load_json injects it at load time.

    # 5. Pipeline Tracking & Metric Fields
    status: Literal["success", "failed"] = Field(description="Processing status")
    error_message: str | None = Field(default=None, description="Error message")
    prompt_tokens: int | None = Field(default=None, description="Prompt tokens")
    completion_tokens: int | None = Field(default=None, description="Completion tokens")
    total_tokens: int | None = Field(default=None, description="Total tokens")
    latency_ms: int | None = Field(default=None, description="API latency in ms")
