#!/usr/bin/env bash
set -euo pipefail

# One-time manual bootstrap for the Briefolio Seed project.
# Terraform cannot create the bucket that will host its own state,
# so this step runs outside Terraform (see TRANSITION.md 7.3, 8).

PROJECT_ID="briefolio-seed"
BUCKET="briefolio-tfstate"
REGION="us-west1"

# 1. Create the project (skip if it already exists).
if ! gcloud projects describe "${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud projects create "${PROJECT_ID}" --name="Briefolio Seed"
fi

# 2. Link billing account (replace with the target billing account ID).
# gcloud billing accounts list
# gcloud billing projects link "${PROJECT_ID}" --billing-account=<BILLING_ACCOUNT_ID>

# 3. Enable Cloud Storage API.
gcloud services enable storage.googleapis.com --project="${PROJECT_ID}"

# 4. Create the Terraform state bucket (skip if it already exists).
if ! gcloud storage buckets describe "gs://${BUCKET}" >/dev/null 2>&1; then
  gcloud storage buckets create "gs://${BUCKET}" \
    --project="${PROJECT_ID}" \
    --location="${REGION}" \
    --uniform-bucket-level-access
fi

# 5. Enable versioning for state recovery.
gcloud storage buckets update "gs://${BUCKET}" --versioning
