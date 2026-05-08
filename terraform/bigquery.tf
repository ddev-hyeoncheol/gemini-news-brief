resource "google_bigquery_dataset" "dataset-bronze" {
  dataset_id                      = "bronze"
  location                        = "us-west1"
  project                         = "gemini-ddev-hyeoncheol-1"

  delete_contents_on_destroy      = false
}

resource "google_bigquery_table" "table-bronze-news" {
  table_id                 = "news"
  dataset_id               = google_bigquery_dataset.dataset-bronze.dataset_id
  project                  = "gemini-ddev-hyeoncheol-1"

  deletion_protection      = true

  clustering               = ["category", "source", "published_at"]
  time_partitioning {
    field         = "executed_at"
    type          = "DAY"
  }

  schema = jsonencode([{
    description = "Executed at"
    mode        = "REQUIRED"
    name        = "executed_at"
    type        = "TIMESTAMP"
    }, {
    description = "News ID (Hash)"
    mode        = "REQUIRED"
    name        = "news_id"
    type        = "STRING"
    }, {
    description = "Category"
    mode        = "REQUIRED"
    name        = "category"
    type        = "STRING"
    }, {
    description = "Source"
    mode        = "REQUIRED"
    name        = "source"
    type        = "STRING"
    }, {
    description = "Published at"
    mode        = "REQUIRED"
    name        = "published_at"
    type        = "TIMESTAMP"
    }, {
    description = "Title"
    mode        = "REQUIRED"
    name        = "title"
    type        = "STRING"
    }, {
    description = "Author"
    mode        = "NULLABLE"
    name        = "author"
    type        = "STRING"
    }, {
    description = "News URL"
    mode        = "REQUIRED"
    name        = "url"
    type        = "STRING"
    }, {
    description = "Content"
    mode        = "NULLABLE"
    name        = "content"
    type        = "STRING"
    }, {
    description = "Image URL"
    mode        = "NULLABLE"
    name        = "image_url"
    type        = "STRING"
    }, {
    description = "Thumbnail URL"
    mode        = "NULLABLE"
    name        = "thumbnail_url"
    type        = "STRING"
    }, {
    description = "Updated at"
    mode        = "NULLABLE"
    name        = "updated_at"
    type        = "TIMESTAMP"
    }, {
    # Database-managed timestamp. Do not provide a value in the ingestion layer.
    # Generated automatically on write.
    defaultValueExpression = "CURRENT_TIMESTAMP()"
    description            = "Loaded at"
    mode                   = "REQUIRED"
    name                   = "loaded_at"
    type                   = "TIMESTAMP"
    }, {
    description = "Additional metadata"
    mode        = "NULLABLE"
    name        = "metadata"
    type        = "JSON"
    }, {
    description = "HTTP status code"
    mode        = "NULLABLE"
    name        = "status_code"
    type        = "INTEGER"
  }])
}

resource "google_bigquery_dataset" "dataset-silver" {
  dataset_id                      = "silver"
  location                        = "us-west1"
  project                         = "gemini-ddev-hyeoncheol-1"

  delete_contents_on_destroy      = false
}
