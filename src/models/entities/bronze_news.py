from typing import Any

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class BronzeNewsModel(BaseModel):
    """
    Entity model representing the Bronze tier news data.
    Contains raw news items collected directly from external sources.
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

    # 3. Clustering Keys (Order: Low Cardinality to High Cardinality)
    category: str = Field(description="News item category")
    source: str = Field(description="News source identifier")
    published_at: AwareDatetime = Field(description="News item publication timestamp")

    # 4. Core Data Fields
    title: str = Field(description="Original news item title")
    author: str | None = Field(default=None, description="Original news item author")
    url: str = Field(description="Source news item URL")
    content: str | None = Field(default=None, description="Raw news item body text")

    # 5. Supplementary Data Fields
    image_url: str | None = Field(default=None, description="News feed image URL")
    thumbnail_url: str | None = Field(
        default=None, description="News item thumbnail URL"
    )
    updated_at: AwareDatetime | None = Field(
        default=None, description="News item update timestamp"
    )
    # 'loaded_at' is excluded from the model. StoreBase.execute_load_json injects it at load time.
    metadata: dict[str, Any] | None = Field(
        default=None, description="Source-specific supplementary metadata"
    )

    # 6. Processing Diagnostics Fields
    status_code: int | None = Field(
        default=None, description="HTTP status code from news item retrieval"
    )
