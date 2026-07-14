resource "google_firestore_database" "state" {
  name            = "(default)"
  location_id     = "us-west1"
  type            = "FIRESTORE_NATIVE"
  deletion_policy = "DELETE"

  depends_on = [google_project_service.firestore]
}
