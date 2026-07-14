terraform {
  backend "gcs" {
    bucket = "briefolio-tfstate"
    prefix = "intelligence"
  }
}
