import asyncio

from google.cloud import bigquery

from src.config.config import settings
from src.core.logger import get_logger

logger = get_logger(__name__)


class BigQueryProvider:
    """
    Provider class for managing Google BigQuery client and concurrency.
    Handles initialization and provides a shared semaphore for resource throttling.
    """

    def __init__(self, semaphore_limit: int = 10) -> None:
        """
        Initialize the provider.
        Note: This should be instantiated within an async context (e.g., lifespan)
        to ensure the semaphore is bound to the correct event loop.
        """
        self.semaphore = asyncio.Semaphore(semaphore_limit)
        self.client = self._init_client()

    def _init_client(self) -> bigquery.Client | None:
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

    def get_client(self) -> bigquery.Client:
        """Return the BigQuery client, raising RuntimeError if not initialized."""
        if self.client is None:
            raise RuntimeError(
                "BigQuery client is not initialized. Check GCP credentials."
            )
        return self.client
