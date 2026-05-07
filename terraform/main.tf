terraform {
  backend "gcs" {
    bucket = "gemini-ddev-hyeoncheol-1-tfstate"
    prefix = "terraform/state"
  }
}
