from google.cloud import bigquery

from src.config.config import settings
from src.core.logger import get_logger

logger = get_logger(__name__)


def get_bigquery_client() -> bigquery.Client | None:
    """Initialize and return a BigQuery client, or None if credentials are not found."""
    is_gcp = settings.is_gcp
    has_explicit_creds = settings.has_explicit_creds

    if not is_gcp and not has_explicit_creds:
        logger.info(
            "BigQuery client not initialized | reason: no GCP credentials found"
        )
        return None

    try:
        client = bigquery.Client()
        logger.info("BigQuery client initialized | project: %s", client.project)
        return client
    except Exception as e:
        logger.warning("BigQuery client initialization failed | error: %s", str(e))
        return None
