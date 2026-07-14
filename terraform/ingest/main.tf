terraform {
  backend "gcs" {
    bucket = "briefolio-tfstate"
    prefix = "ingest"
  }
}
