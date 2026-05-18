resource "google_bigquery_dataset" "dataset-bronze" {
  dataset_id = "bronze"
  location   = "us-west1"
  project    = "gemini-ddev-hyeoncheol-1"

  delete_contents_on_destroy = false
}

resource "google_bigquery_table" "table-bronze-news" {
  table_id   = "news"
  dataset_id = google_bigquery_dataset.dataset-bronze.dataset_id
  project    = "gemini-ddev-hyeoncheol-1"

  deletion_protection = true

  clustering = ["category", "source", "published_at"]
  time_partitioning {
    field = "executed_at"
    type  = "DAY"
  }

  schema = jsonencode([
    { name = "executed_at",   type = "TIMESTAMP", mode = "REQUIRED", description = "Batch execution timestamp" },
    { name = "news_id",       type = "STRING",    mode = "REQUIRED", description = "Stable unique news item identifier" },
    { name = "category",      type = "STRING",    mode = "REQUIRED", description = "News item category" },
    { name = "source",        type = "STRING",    mode = "REQUIRED", description = "News source identifier" },
    { name = "published_at",  type = "TIMESTAMP", mode = "REQUIRED", description = "News item publication timestamp" },
    { name = "title",         type = "STRING",    mode = "REQUIRED", description = "Original news item title" },
    { name = "author",        type = "STRING",    mode = "NULLABLE", description = "Original news item author" },
    { name = "url",           type = "STRING",    mode = "REQUIRED", description = "Source news item URL" },
    { name = "content",       type = "STRING",    mode = "NULLABLE", description = "Raw news item body text" },
    { name = "image_url",     type = "STRING",    mode = "NULLABLE", description = "News feed image URL" },
    { name = "thumbnail_url", type = "STRING",    mode = "NULLABLE", description = "News item thumbnail URL" },
    { name = "updated_at",    type = "TIMESTAMP", mode = "NULLABLE", description = "News item update timestamp" },
    # Application-injected load timestamp. StoreBase.execute_load_json sets this before BigQuery load jobs.
    { name = "loaded_at",     type = "TIMESTAMP", mode = "NULLABLE", description = "Record load timestamp", defaultValueExpression = "CURRENT_TIMESTAMP()" },
    { name = "metadata",      type = "JSON",      mode = "NULLABLE", description = "Source-specific supplementary metadata" },
    { name = "status_code",   type = "INTEGER",   mode = "NULLABLE", description = "HTTP status code from news item retrieval" },
  ])
}
