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
            "Local environment detected without GOOGLE_APPLICATION_CREDENTIALS. "
            "Running BigQuery operations in MOCK mode."
        )
        return None

    try:
        return bigquery.Client()
    except Exception as e:
        logger.warning(
            "Failed to initialize BigQuery client: %s. Running operations in MOCK mode.",
            str(e),
        )
        return None
