resource "google_firestore_database" "ingest" {
  name        = "(default)"
  location_id = "us-west1"
  type        = "FIRESTORE_NATIVE"

  delete_protection_state = "DELETE_PROTECTION_ENABLED"
  depends_on              = [google_project_service.firestore]
}
