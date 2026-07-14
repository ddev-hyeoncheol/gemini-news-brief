resource "google_storage_bucket" "raw" {
  name                        = "briefolio-ingest-raw"
  location                    = "us-west1"
  force_destroy               = true
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  depends_on = [google_project_service.storage]
}
