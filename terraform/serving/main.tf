terraform {
  backend "gcs" {
    bucket = "briefolio-tfstate"
    prefix = "serving"
  }
}
