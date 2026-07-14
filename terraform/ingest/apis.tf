resource "google_project_service" "firestore" {
  service            = "firestore.googleapis.com"
  disable_on_destroy = true
}

resource "google_project_service" "storage" {
  service            = "storage.googleapis.com"
  disable_on_destroy = true
}
