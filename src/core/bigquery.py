import os

from google.cloud import bigquery

from src.core.logger import get_logger

logger = get_logger(__name__)


def get_bigquery_client() -> bigquery.Client | None:
    """Initialize and return a BigQuery client, or None if credentials are not found."""
    is_gcp = os.environ.get("K_SERVICE") is not None
    has_explicit_creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") is not None

    if not is_gcp and not has_explicit_creds:
        logger.info(
            "BigQuery client not initialized | reason: no GCP credentials found"
        )
        return None

    try:
        return bigquery.Client()
    except Exception as e:
        logger.warning("BigQuery client initialization failed | error: %s", str(e))
        return None
