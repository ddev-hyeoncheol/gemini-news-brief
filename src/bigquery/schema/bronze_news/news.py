from google.cloud import bigquery

TABLE_NAME = "news"

PARTITION_FIELD = "collected_at"
PARTITION_TYPE = "HOUR"

SCHEMA = [
    bigquery.SchemaField(
        name="news_id", type="STRING", mode="REQUIRED", description="뉴스 ID(Hash)"
    ),
    bigquery.SchemaField(
        name="title", type="STRING", mode="REQUIRED", description="제목"
    ),
    bigquery.SchemaField(
        name="url", type="STRING", mode="REQUIRED", description="뉴스 URL"
    ),
    bigquery.SchemaField(
        name="content", type="STRING", mode="NULLABLE", description="본문"
    ),
    bigquery.SchemaField(
        name="source", type="STRING", mode="NULLABLE", description="출처"
    ),
    bigquery.SchemaField(
        name="category", type="STRING", mode="NULLABLE", description="카테고리"
    ),
    bigquery.SchemaField(
        name="author", type="STRING", mode="NULLABLE", description="작성자"
    ),
    bigquery.SchemaField(
        name="published_at", type="TIMESTAMP", mode="NULLABLE", description="발행일시"
    ),
    bigquery.SchemaField(
        name="collected_at", type="TIMESTAMP", mode="REQUIRED", description="수집일시"
    ),
]
