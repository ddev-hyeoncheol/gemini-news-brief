resource "google_bigquery_dataset" "dataset-bronze" {
  dataset_id = "bronze"
  location   = "us-west1"
  project    = var.project_id

  delete_contents_on_destroy = false
}

resource "google_bigquery_table" "table-bronze-news" {
  table_id   = "news"
  dataset_id = google_bigquery_dataset.dataset-bronze.dataset_id
  project    = var.project_id

  deletion_protection = true

  clustering = ["entry_id", "news_id", "source"]
  time_partitioning {
    field = "executed_at"
    type  = "DAY"
  }

  schema = jsonencode([
    # Identity & Partitioning
    { name = "executed_at", type = "TIMESTAMP", mode = "REQUIRED", description = "Batch execution timestamp" },
    { name = "entry_id", type = "STRING", mode = "REQUIRED", description = "Stable RSS entry identifier" },
    { name = "news_id", type = "STRING", mode = "REQUIRED", description = "Stable news item identifier" },
    { name = "source", type = "STRING", mode = "REQUIRED", description = "RSS feed provider identifier" },

    # RSS fetch (feedparser)
    { name = "title", type = "STRING", mode = "REQUIRED", description = "RSS-provided news item title" },
    { name = "entry_url", type = "STRING", mode = "REQUIRED", description = "RSS-provided news item URL" },
    { name = "published_at", type = "TIMESTAMP", mode = "REQUIRED", description = "RSS-provided publication timestamp" },
    { name = "updated_at", type = "TIMESTAMP", mode = "NULLABLE", description = "RSS-provided update timestamp" },
    { name = "original_source_name", type = "STRING", mode = "NULLABLE", description = "RSS-provided original publisher name" },
    { name = "original_source_url", type = "STRING", mode = "NULLABLE", description = "RSS-provided original publisher URL" },
    { name = "thumbnail_url", type = "STRING", mode = "NULLABLE", description = "RSS-provided thumbnail image URL" },

    # HTML enrich (newspaper4k)
    { name = "authors", type = "STRING", mode = "NULLABLE", description = "HTML-extracted author names" },
    { name = "canonical_url", type = "STRING", mode = "NULLABLE", description = "HTML-declared canonical URL" },
    { name = "image_url", type = "STRING", mode = "NULLABLE", description = "HTML-extracted representative image URL" },
    { name = "language", type = "STRING", mode = "NULLABLE", description = "HTML-declared language code" },
    { name = "content", type = "STRING", mode = "NULLABLE", description = "HTML-extracted article body text" },

    # Processing diagnostics
    { name = "status", type = "STRING", mode = "NULLABLE", description = "Bronze item ingestion status" },
    { name = "status_code", type = "INTEGER", mode = "NULLABLE", description = "Bronze item ingestion HTTP status code; 0 indicates a network error" },
    { name = "error_message", type = "STRING", mode = "NULLABLE", description = "Bronze item ingestion error message" },

    # Source metadata
    { name = "metadata", type = "JSON", mode = "NULLABLE", description = "Source-specific RSS metadata" },

    # System audit
    # Application-injected load timestamp. BigQueryProvider.execute_load_json sets this before BigQuery load jobs.
    { name = "loaded_at", type = "TIMESTAMP", mode = "NULLABLE", description = "Application-injected load timestamp" },
  ])
}
