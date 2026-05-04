from typing import Any
from pydantic import BaseModel, Field, ConfigDict, AwareDatetime


class BronzeNewsModel(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        frozen=True,
    )

    news_id: str = Field(description="News ID (Hash)")
    source: str = Field(description="Source")
    title: str = Field(description="Title")
    url: str = Field(description="News URL")
    content: str | None = Field(default=None, description="Content")
    author: str | None = Field(default=None, description="Author")
    category: str | None = Field(default="finance", description="Category")
    image_url: str | None = Field(default=None, description="Image URL")
    thumbnail_url: str | None = Field(default=None, description="Thumbnail URL")
    published_at: AwareDatetime = Field(description="Published at")
    updated_at: AwareDatetime | None = Field(default=None, description="Updated at")
    executed_at: AwareDatetime = Field(description="Executed at")
    # 'loaded_at' is excluded here to trigger BigQuery's server-side CURRENT_TIMESTAMP() default.
    # Do not add to prevent null overrides.
    metadata: dict[str, Any] | None = Field(
        default=None, description="Additional metadata"
    )
