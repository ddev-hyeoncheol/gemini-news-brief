from pydantic import BaseModel, Field, ConfigDict, AwareDatetime


class SilverNewsModel(BaseModel):
    """
    Entity model representing the Silver tier news data.
    Contains structured news articles ready for analysis and AI augmentation.
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
    author_raw: str | None = Field(default=None, description="Raw Author")
    url: str = Field(description="News URL")
    content_raw: str = Field(description="Raw content")

    # 5. Supplementary Data Fields
    image_url: str | None = Field(default=None, description="Image URL")
    thumbnail_url: str | None = Field(default=None, description="Thumbnail URL")
    updated_at: AwareDatetime | None = Field(default=None, description="Updated at")
    # 'loaded_at' is excluded here to trigger BigQuery's server-side CURRENT_TIMESTAMP() default.
    # Do not add to prevent null overrides.
