resource "google_bigquery_dataset" "dataset-silver" {
  dataset_id = "silver"
  location   = "us-west1"
  project    = var.project_id

  delete_contents_on_destroy = false
}

resource "google_bigquery_table" "table-silver-news" {
  table_id   = "news"
  dataset_id = google_bigquery_dataset.dataset-silver.dataset_id
  project    = var.project_id

  deletion_protection = true

  clustering = ["category", "source", "published_at"]
  time_partitioning {
    field = "executed_at"
    type  = "DAY"
  }

  schema = jsonencode([
    { name = "executed_at", type = "TIMESTAMP", mode = "REQUIRED", description = "Batch execution timestamp" },
    { name = "news_id", type = "STRING", mode = "REQUIRED", description = "Stable unique news item identifier" },
    { name = "category", type = "STRING", mode = "REQUIRED", description = "News item category" },
    { name = "source", type = "STRING", mode = "REQUIRED", description = "News source identifier" },
    { name = "published_at", type = "TIMESTAMP", mode = "REQUIRED", description = "News item publication timestamp" },
    { name = "title", type = "STRING", mode = "REQUIRED", description = "Original news item title" },
    { name = "author_raw", type = "STRING", mode = "NULLABLE", description = "Raw news item author" },
    { name = "url", type = "STRING", mode = "REQUIRED", description = "Source news item URL" },
    { name = "content_raw", type = "STRING", mode = "REQUIRED", description = "Raw news item body text" },
    { name = "image_url", type = "STRING", mode = "NULLABLE", description = "News feed image URL" },
    { name = "thumbnail_url", type = "STRING", mode = "NULLABLE", description = "News item thumbnail URL" },
    { name = "updated_at", type = "TIMESTAMP", mode = "NULLABLE", description = "News item update timestamp" },
    # Application-injected load timestamp. StoreBase.execute_load_json sets this before BigQuery load jobs.
    { name = "loaded_at", type = "TIMESTAMP", mode = "NULLABLE", description = "Record load timestamp" },
  ])
}

resource "google_bigquery_table" "table-silver-news-augmented" {
  table_id   = "news_augmented"
  dataset_id = google_bigquery_dataset.dataset-silver.dataset_id
  project    = var.project_id

  deletion_protection = true

  clustering = ["news_id", "model", "version"]
  time_partitioning {
    field = "executed_at"
    type  = "DAY"
  }

  schema = jsonencode([
    { name = "executed_at", type = "TIMESTAMP", mode = "REQUIRED", description = "Batch execution timestamp" },
    { name = "news_id", type = "STRING", mode = "REQUIRED", description = "Stable unique news item identifier" },
    { name = "model", type = "STRING", mode = "REQUIRED", description = "LLM model name" },
    { name = "version", type = "STRING", mode = "REQUIRED", description = "LLM analysis schema version" },
    { name = "ai_sector", type = "STRING", mode = "NULLABLE", description = "AI-classified economic sector" },
    { name = "ai_format", type = "STRING", mode = "NULLABLE", description = "AI-classified news item format" },
    { name = "ai_sentiment", type = "STRING", mode = "NULLABLE", description = "AI-classified news item sentiment" },
    { name = "ai_title", type = "STRING", mode = "NULLABLE", description = "Korean translation of the news item title" },
    { name = "ai_author", type = "STRING", mode = "REPEATED", description = "Normalized news item author names" },
    { name = "ai_summary", type = "STRING", mode = "NULLABLE", description = "Korean summary of the news item" },
    { name = "ai_content_clean", type = "STRING", mode = "NULLABLE", description = "News item body text with boilerplate removed" },
    # Application-injected load timestamp. StoreBase.execute_load_json sets this before BigQuery load jobs.
    { name = "loaded_at", type = "TIMESTAMP", mode = "NULLABLE", description = "Record load timestamp" },
    { name = "batch_id", type = "STRING", mode = "REQUIRED", description = "LLM request batch identifier" },
    { name = "status", type = "STRING", mode = "REQUIRED", description = "AI augmentation processing status" },
    { name = "error_message", type = "STRING", mode = "NULLABLE", description = "AI augmentation error message" },
  ])
}
