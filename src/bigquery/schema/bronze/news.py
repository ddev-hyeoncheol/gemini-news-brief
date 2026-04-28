from google.cloud import bigquery

TABLE_NAME = "news"

# Partitioning object for table creation/update
TIME_PARTITIONING = bigquery.TimePartitioning(
    type_=bigquery.TimePartitioningType.HOUR,
    field="executed_at",
)

# Clustering fields to improve query performance and reduce costs (Max 4)
CLUSTERING_FIELDS = ["source", "category"]

SCHEMA = [
    bigquery.SchemaField(
        name="news_id",
        field_type="STRING",
        mode="REQUIRED",
        description="News ID (Hash)",
    ),
    bigquery.SchemaField(
        name="source",
        field_type="STRING",
        mode="REQUIRED",
        description="Source",
    ),
    bigquery.SchemaField(
        name="title",
        field_type="STRING",
        mode="REQUIRED",
        description="Title",
    ),
    bigquery.SchemaField(
        name="url",
        field_type="STRING",
        mode="REQUIRED",
        description="News URL",
    ),
    bigquery.SchemaField(
        name="content",
        field_type="STRING",
        mode="NULLABLE",
        description="Content",
    ),
    bigquery.SchemaField(
        name="author",
        field_type="STRING",
        mode="NULLABLE",
        description="Author",
    ),
    bigquery.SchemaField(
        name="category",
        field_type="STRING",
        mode="NULLABLE",
        description="Category",
    ),
    bigquery.SchemaField(
        name="image_url",
        field_type="STRING",
        mode="NULLABLE",
        description="Image URL",
    ),
    bigquery.SchemaField(
        name="thumbnail_url",
        field_type="STRING",
        mode="NULLABLE",
        description="Thumbnail URL",
    ),
    bigquery.SchemaField(
        name="published_at",
        field_type="TIMESTAMP",
        mode="REQUIRED",
        description="Published at",
    ),
    bigquery.SchemaField(
        name="updated_at",
        field_type="TIMESTAMP",
        mode="NULLABLE",
        description="Updated at",
    ),
    bigquery.SchemaField(
        name="executed_at",
        field_type="TIMESTAMP",
        mode="REQUIRED",
        description="Executed at",
    ),
    # Database-managed timestamp. Do not provide a value in the ingestion layer.
    # generated automatically on write.
    bigquery.SchemaField(
        name="loaded_at",
        field_type="TIMESTAMP",
        mode="REQUIRED",
        default_value_expression="CURRENT_TIMESTAMP()",
        description="Loaded at",
    ),
    bigquery.SchemaField(
        name="metadata",
        field_type="JSON",
        mode="NULLABLE",
        description="Additional metadata",
    ),
]
