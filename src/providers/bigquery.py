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

    def __init__(self, semaphore: asyncio.Semaphore) -> None:
        """
        Initialize the provider with an injected semaphore.
        The semaphore should be created within an async context (e.g., lifespan)
        to ensure it is bound to the correct event loop.
        """
        self.semaphore = semaphore
        self.client = self._init_client()

    def get_client(self) -> bigquery.Client:
        """Return the BigQuery client, raising RuntimeError if not initialized."""
        if self.client is None:
            raise RuntimeError(
                "BigQuery client is not initialized. Check GCP credentials."
            )
        return self.client

    def _init_client(self) -> bigquery.Client | None:
        """Initialize and return a BigQuery client, or None if credentials are not found."""
        is_gcp = settings.is_gcp
        has_explicit_creds = settings.has_explicit_creds

        if not is_gcp and not has_explicit_creds:
            logger.info(
                "Provider initialize skipped | provider: bigquery, reason: no GCP credentials found"
            )
            return None

        try:
            client = bigquery.Client(project=settings.gcp_project_id)
            logger.info(
                "Provider initialize completed | provider: bigquery, project: %s",
                client.project,
            )
            return client
        except Exception as e:
            logger.warning(
                "Provider initialize failed | provider: bigquery, error: %s",
                str(e),
            )
            return None
