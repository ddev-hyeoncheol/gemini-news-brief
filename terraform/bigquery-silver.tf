resource "google_bigquery_dataset" "dataset-silver" {
  dataset_id  = "silver"
  location    = "us-west1"
  project     = "gemini-ddev-hyeoncheol-1"

  delete_contents_on_destroy  = false
}

resource "google_bigquery_table" "table-silver-news" {
  table_id    = "news"
  dataset_id  = google_bigquery_dataset.dataset-silver.dataset_id
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
    { name = "author_raw",      type = "STRING",      mode = "NULLABLE",    description = "Raw Author" },
    { name = "url",             type = "STRING",      mode = "REQUIRED",    description = "News URL" },
    { name = "content_raw",     type = "STRING",      mode = "REQUIRED",    description = "Raw content" },
    { name = "image_url",       type = "STRING",      mode = "NULLABLE",    description = "Image URL" },
    { name = "thumbnail_url",   type = "STRING",      mode = "NULLABLE",    description = "Thumbnail URL" },
    { name = "updated_at",      type = "TIMESTAMP",   mode = "NULLABLE",    description = "Updated at" },
    # Database-managed timestamp. Do not provide a value in the ingestion layer.
    # Generated automatically on write.
    { name = "loaded_at",       type = "TIMESTAMP",   mode = "NULLABLE",    description = "Loaded at",
      defaultValueExpression = "CURRENT_TIMESTAMP()" },
  ])
}

resource "google_bigquery_table" "table-silver-news-augmented" {
  table_id    = "news_augmented"
  dataset_id  = google_bigquery_dataset.dataset-silver.dataset_id
  project     = "gemini-ddev-hyeoncheol-1"

  deletion_protection = true

  clustering  = ["news_id", "model", "version"]
  time_partitioning {
    field = "executed_at"
    type  = "DAY"
  }

  schema = jsonencode([
    { name = "executed_at",       type = "TIMESTAMP",   mode = "REQUIRED",    description = "Executed at" },
    { name = "news_id",           type = "STRING",      mode = "REQUIRED",    description = "News ID (Hash)" },
    { name = "model",             type = "STRING",      mode = "REQUIRED",    description = "LLM model name" },
    { name = "version",           type = "STRING",      mode = "REQUIRED",    description = "LLM model version" },
    { name = "ai_sector",         type = "STRING",      mode = "NULLABLE",    description = "AI-determined economic sector" },
    { name = "ai_format",         type = "STRING",      mode = "NULLABLE",    description = "AI-determined article format" },
    { name = "ai_sentiment",      type = "STRING",      mode = "NULLABLE",    description = "AI-determined sentiment" },
    { name = "ai_title",          type = "STRING",      mode = "NULLABLE",    description = "AI-translated title in Korean" },
    { name = "ai_author",         type = "STRING",      mode = "REPEATED",    description = "AI-determined authors" },
    { name = "ai_summary",        type = "STRING",      mode = "NULLABLE",    description = "AI-generated summary in Korean" },
    { name = "ai_content_clean",  type = "STRING",      mode = "NULLABLE",    description = "AI-cleaned content" },
    # Database-managed timestamp. Do not provide a value in the ingestion layer.
    # Generated automatically on write.
    { name = "loaded_at",         type = "TIMESTAMP",   mode = "NULLABLE",    description = "Loaded at",
      defaultValueExpression = "CURRENT_TIMESTAMP()" },
    { name = "batch_id",          type = "STRING",      mode = "REQUIRED",    description = "Batch ID (Hash of news IDs in the batch)" },
    { name = "status",            type = "STRING",      mode = "REQUIRED",    description = "Processing status" },
    { name = "error_message",     type = "STRING",      mode = "NULLABLE",    description = "Error message" },
  ])
}
