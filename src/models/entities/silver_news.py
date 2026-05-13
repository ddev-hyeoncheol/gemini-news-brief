from pydantic import BaseModel, Field, ConfigDict, AwareDatetime

from src.models.entities.bronze_news import BronzeNewsModel


class SilverNewsModel(BaseModel):
    """
    Entity model representing the Silver tier news data.
    Contains structured news articles ready for analysis and AI augmentation.
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
    # 'loaded_at' is excluded from the model. StoreBase.execute_load_json injects it at load time.

    @classmethod
    def from_bronze_news(cls, bronze_news: BronzeNewsModel) -> "SilverNewsModel | None":
        """
        Transform a Bronze tier news entity into a Silver tier entity.
        Return None if the source item failed to fetch content (status_code != 200 or content is None).
        """
        if bronze_news.status_code != 200 or bronze_news.content is None:
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
        Transform a list of Bronze tier entities into Silver tier entities.
        Filter out items that failed to fetch content automatically.
        """
        return [
            silver
            for bronze_news in bronze_news_list
            if (silver := cls.from_bronze_news(bronze_news)) is not None
        ]
