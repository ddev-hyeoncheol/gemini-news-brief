terraform {
  backend "gcs" {
    bucket = "briefolio-tfstate"
    prefix = "terraform/state/ingest"
  }
}
