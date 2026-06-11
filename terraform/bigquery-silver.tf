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

  clustering = ["news_id", "published_at"]
  time_partitioning {
    field = "executed_at"
    type  = "DAY"
  }

  schema = jsonencode([
    # Identity & Partitioning
    { name = "executed_at", type = "TIMESTAMP", mode = "REQUIRED", description = "Batch execution timestamp" },
    { name = "news_id", type = "STRING", mode = "REQUIRED", description = "Stable article URL-based news item identifier" },
    { name = "source", type = "STRING", mode = "REQUIRED", description = "News item source identifier" },

    # News Item Fields
    { name = "title", type = "STRING", mode = "REQUIRED", description = "News item title" },
    { name = "url", type = "STRING", mode = "REQUIRED", description = "News item representative URL" },
    { name = "published_at", type = "TIMESTAMP", mode = "REQUIRED", description = "News item publication timestamp" },
    { name = "updated_at", type = "TIMESTAMP", mode = "NULLABLE", description = "News item update timestamp" },

    # Bronze Raw Fields
    { name = "raw_authors", type = "STRING", mode = "NULLABLE", description = "Bronze raw pipe-delimited author names" },
    { name = "raw_content", type = "STRING", mode = "REQUIRED", description = "Bronze raw article body text" },

    # News Item Metadata
    { name = "image_url", type = "STRING", mode = "NULLABLE", description = "News item representative image URL" },
    { name = "thumbnail_url", type = "STRING", mode = "NULLABLE", description = "News item thumbnail image URL" },
    { name = "language", type = "STRING", mode = "NULLABLE", description = "News item language code" },

    # Load Audit
    # Application-injected load timestamp. BigQueryProvider.execute_load_json sets this before BigQuery load jobs.
    { name = "loaded_at", type = "TIMESTAMP", mode = "NULLABLE", description = "Application-injected load timestamp" },
  ])
}

resource "google_bigquery_table" "table-silver-news-augmented" {
  table_id   = "news_augmented"
  dataset_id = google_bigquery_dataset.dataset-silver.dataset_id
  project    = var.project_id

  deletion_protection = true

  clustering = ["news_id", "model_provider", "model_name", "analysis_version"]
  time_partitioning {
    field = "executed_at"
    type  = "DAY"
  }

  schema = jsonencode([
    # Identity & Partitioning
    { name = "executed_at", type = "TIMESTAMP", mode = "REQUIRED", description = "Batch execution timestamp" },
    { name = "news_id", type = "STRING", mode = "REQUIRED", description = "Stable article URL-based news item identifier" },

    # LLM Metadata
    { name = "model_provider", type = "STRING", mode = "REQUIRED", description = "LLM provider name" },
    { name = "model_name", type = "STRING", mode = "REQUIRED", description = "LLM model name" },
    { name = "analysis_version", type = "STRING", mode = "REQUIRED", description = "AI analysis contract version" },

    # AI Classification
    { name = "ai_category", type = "STRING", mode = "NULLABLE", description = "AI-classified economic news category" },
    { name = "ai_format", type = "STRING", mode = "NULLABLE", description = "AI-classified news item format" },
    { name = "ai_sentiment", type = "STRING", mode = "NULLABLE", description = "AI-classified news item sentiment" },

    # AI Market Entities
    {
      name = "ai_market_entities", type = "RECORD", mode = "REPEATED", description = "AI-extracted market entities",
      fields = [
        { name = "entity_type", type = "STRING", mode = "REQUIRED", description = "AI-classified market entity type" },
        { name = "name", type = "STRING", mode = "NULLABLE", description = "AI-identified market entity name" },
        { name = "symbol", type = "STRING", mode = "NULLABLE", description = "AI-identified ticker or market symbol" },
      ]
    },

    # AI Cleanup Outputs
    { name = "ai_authors", type = "STRING", mode = "REPEATED", description = "AI-cleaned author names" },
    { name = "ai_content", type = "STRING", mode = "NULLABLE", description = "AI-cleaned article body text" },

    # AI Korean Outputs
    { name = "ai_title_ko", type = "STRING", mode = "NULLABLE", description = "AI-translated news item title in Korean" },
    { name = "ai_summary_ko", type = "STRING", mode = "NULLABLE", description = "AI-generated news item summary in Korean" },
    { name = "ai_summary_bullets_ko", type = "STRING", mode = "REPEATED", description = "AI-generated bullet point news item summary in Korean" },
    { name = "ai_content_ko", type = "STRING", mode = "NULLABLE", description = "AI-translated article body text in Korean" },

    # Processing Diagnostics
    { name = "batch_id", type = "STRING", mode = "NULLABLE", description = "Deterministic LLM chunk batch identifier" },
    { name = "status", type = "STRING", mode = "REQUIRED", description = "AI augmentation processing status" },
    { name = "error_message", type = "STRING", mode = "NULLABLE", description = "AI augmentation error message" },

    # Load Audit
    # Application-injected load timestamp. BigQueryProvider.execute_load_json sets this before BigQuery load jobs.
    { name = "loaded_at", type = "TIMESTAMP", mode = "NULLABLE", description = "Application-injected load timestamp" },
  ])
}
