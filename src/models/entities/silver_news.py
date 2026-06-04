from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from src.models.entities.bronze_news import BronzeNewsModel


class SilverNewsModel(BaseModel):
    """
    Entity model representing the Silver tier news data.
    Contains structured news items ready for analysis and AI augmentation.
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
    source: str = Field(description="News item source identifier")

    # News Item Fields
    title: str = Field(description="News item title")
    url: str = Field(description="News item representative URL")
    published_at: AwareDatetime = Field(description="News item publication timestamp")
    updated_at: AwareDatetime | None = Field(default=None, description="News item update timestamp")

    # Bronze Raw Fields
    raw_authors: str | None = Field(default=None, description="Bronze raw pipe-delimited author names")
    raw_content: str = Field(description="Bronze raw article body text")

    # News Item Metadata
    image_url: str | None = Field(default=None, description="News item representative image URL")
    thumbnail_url: str | None = Field(default=None, description="News item thumbnail image URL")
    language: str | None = Field(default=None, description="News item language code")

    @classmethod
    def from_bronze_news(cls, bronze_news: BronzeNewsModel) -> "SilverNewsModel | None":
        """
        Transform a Bronze tier news item into a Silver tier news item.
        Return None unless the Bronze item is successful.
        """
        # Success means status_code == 200 and raw content is present.
        # Keep the explicit content check for Pyright type narrowing.
        if bronze_news.status != "success" or bronze_news.content is None:
            return None

        return cls(
            executed_at=bronze_news.executed_at,
            news_id=bronze_news.news_id,
            source=bronze_news.source,
            title=bronze_news.title,
            url=bronze_news.canonical_url or bronze_news.entry_url,
            published_at=bronze_news.published_at,
            updated_at=bronze_news.updated_at,
            raw_authors=bronze_news.authors,
            raw_content=bronze_news.content,
            image_url=bronze_news.image_url,
            thumbnail_url=bronze_news.thumbnail_url,
            language=bronze_news.language,
        )

    @classmethod
    def from_bronze_news_list(cls, bronze_news_list: list[BronzeNewsModel]) -> list["SilverNewsModel"]:
        """
        Transform Bronze tier news items into Silver tier news items.
        Filter out items that failed to fetch content.
        """
        return [silver for bronze_news in bronze_news_list if (silver := cls.from_bronze_news(bronze_news)) is not None]
