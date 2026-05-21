from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from src.models.entities.bronze_news import BronzeNewsModel


class SilverNewsModel(BaseModel):
    """
    Entity model representing the Silver tier news data.
    Contains structured news items ready for analysis and AI augmentation.
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
    author_raw: str | None = Field(default=None, description="Raw news item author")
    url: str = Field(description="Source news item URL")
    content_raw: str = Field(description="Raw news item body text")

    # 5. Supplementary Data Fields
    image_url: str | None = Field(default=None, description="News feed image URL")
    thumbnail_url: str | None = Field(
        default=None, description="News item thumbnail URL"
    )
    updated_at: AwareDatetime | None = Field(
        default=None, description="News item update timestamp"
    )
    # 'loaded_at' is excluded from the model. StoreBase.execute_load_json injects it at load time.

    @classmethod
    def from_bronze_news(cls, bronze_news: BronzeNewsModel) -> "SilverNewsModel | None":
        """
        Transform a Bronze tier news item into a Silver tier news item.
        Return None if the source item failed to fetch non-empty content.
        """
        if bronze_news.status_code != 200 or not bronze_news.content:
            return None

        return cls(
            executed_at=bronze_news.executed_at,
            news_id=bronze_news.news_id,
            category=bronze_news.category,
            source=bronze_news.source,
            published_at=bronze_news.published_at,
            title=bronze_news.title,
            author_raw=bronze_news.author,
            url=bronze_news.url,
            content_raw=bronze_news.content,
            image_url=bronze_news.image_url,
            thumbnail_url=bronze_news.thumbnail_url,
            updated_at=bronze_news.updated_at,
        )

    @classmethod
    def from_bronze_news_list(
        cls, bronze_news_list: list[BronzeNewsModel]
    ) -> list["SilverNewsModel"]:
        """
        Transform Bronze tier news items into Silver tier news items.
        Filter out items that failed to fetch content.
        """
        return [
            silver
            for bronze_news in bronze_news_list
            if (silver := cls.from_bronze_news(bronze_news)) is not None
        ]
