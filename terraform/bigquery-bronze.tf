resource "google_bigquery_dataset" "dataset-bronze" {
  dataset_id  = "bronze"
  location    = "us-west1"
  project     = "gemini-ddev-hyeoncheol-1"

  delete_contents_on_destroy  = false
}

resource "google_bigquery_table" "table-bronze-news" {
  table_id    = "news"
  dataset_id  = google_bigquery_dataset.dataset-bronze.dataset_id
  project     = "gemini-ddev-hyeoncheol-1"

  deletion_protection = true

  clustering  = ["category", "source", "published_at"]
  time_partitioning {
    field = "executed_at"
    type  = "DAY"
  }

  schema = jsonencode([
    { name = "executed_at",     type = "TIMESTAMP",   mode = "REQUIRED",    description = "Executed at" },
    { name = "news_id",         type = "STRING",      mode = "REQUIRED",    description = "News ID (Hash)" },
    { name = "category",        type = "STRING",      mode = "REQUIRED",    description = "Category" },
    { name = "source",          type = "STRING",      mode = "REQUIRED",    description = "Source" },
    { name = "published_at",    type = "TIMESTAMP",   mode = "REQUIRED",    description = "Published at" },
    { name = "title",           type = "STRING",      mode = "REQUIRED",    description = "Title" },
    { name = "author",          type = "STRING",      mode = "NULLABLE",    description = "Author" },
    { name = "url",             type = "STRING",      mode = "REQUIRED",    description = "News URL" },
    { name = "content",         type = "STRING",      mode = "NULLABLE",    description = "Content" },
    { name = "image_url",       type = "STRING",      mode = "NULLABLE",    description = "Image URL" },
    { name = "thumbnail_url",   type = "STRING",      mode = "NULLABLE",    description = "Thumbnail URL" },
    { name = "updated_at",      type = "TIMESTAMP",   mode = "NULLABLE",    description = "Updated at" },
    # Database-managed timestamp. Do not provide a value in the ingestion layer.
    # Generated automatically on write.
    { name = "loaded_at",       type = "TIMESTAMP",   mode = "NULLABLE",    description = "Loaded at",
      defaultValueExpression = "CURRENT_TIMESTAMP()" },
    { name = "metadata",        type = "JSON",        mode = "NULLABLE",    description = "Additional metadata" },
    { name = "status_code",     type = "INTEGER",     mode = "NULLABLE",    description = "HTTP status code" },
  ])
}
