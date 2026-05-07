terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = "gemini-ddev-hyeoncheol-1"
  region  = "us-west1"
}
