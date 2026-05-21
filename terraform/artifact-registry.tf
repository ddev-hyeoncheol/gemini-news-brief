resource "google_artifact_registry_repository" "default" {
  location      = "us-west1"
  repository_id = "gemini-news-brief-fastapi"
  description   = "Docker image repository for Gemini News Brief"
  format        = "DOCKER"
}
