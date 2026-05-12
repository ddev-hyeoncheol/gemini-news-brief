from typing import Any
from pydantic import BaseModel, Field, ConfigDict, AwareDatetime


class BronzeNewsModel(BaseModel):
    """
    Entity model representing the Bronze tier news data.
    Contains raw news articles collected directly from external sources.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        frozen=True,
    )

    # 1. Partition Key
    executed_at: AwareDatetime = Field(description="Executed at")

    # 2. Identification Keys
    news_id: str = Field(description="News ID (Hash)")

    # 3. Clustering Keys (Order: Low Cardinality to High Cardinality)
    category: str = Field(description="Category")
    source: str = Field(description="Source")
    published_at: AwareDatetime = Field(description="Published at")

    # 4. Core Data Fields
    title: str = Field(description="Title")
    author: str | None = Field(default=None, description="Author")
    url: str = Field(description="News URL")
    content: str | None = Field(default=None, description="Content")

    # 5. Supplementary Data Fields
    image_url: str | None = Field(default=None, description="Image URL")
    thumbnail_url: str | None = Field(default=None, description="Thumbnail URL")
    updated_at: AwareDatetime | None = Field(default=None, description="Updated at")
    loaded_at: AwareDatetime | None = Field(default=None, description="Loaded at")
    metadata: dict[str, Any] | None = Field(
        default=None, description="Additional metadata"
    )

    # 6. Pipeline Tracking Fields
    status_code: int | None = Field(default=None, description="HTTP status code")
