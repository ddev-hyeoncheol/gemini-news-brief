from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings mapped from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application HTTP port. Cloud Run provides PORT; local runs use the same default.
    port: int = 8080

    # Application log level.
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # Cloud Run automatically sets K_SERVICE; use it to detect GCP environment.
    k_service: str | None = None

    # Explicit credentials for local BigQuery access.
    google_application_credentials: str | None = None

    # GCP project identifiers. Cloud Build sets GOOGLE_CLOUD_PROJECT; GCP_PROJECT is a fallback.
    google_cloud_project: str | None = None
    gcp_project: str | None = None

    # Gemini API keys configured from local .env or Cloud Run secrets.
    gemini_api_key_free: str | None = None
    gemini_api_key_paid: str | None = None

    @property
    def is_gcp(self) -> bool:
        """Return True if the application is running on GCP (Cloud Run)."""
        return self.k_service is not None

    @property
    def has_explicit_creds(self) -> bool:
        """Return True if explicit GCP credentials are configured via environment variable."""
        return bool(self.google_application_credentials)

    @property
    def gcp_project_id(self) -> str | None:
        """Return the configured GCP project identifier if available."""
        return self.google_cloud_project or self.gcp_project


settings = Settings()


def get_settings() -> Settings:
    """Provide the shared Settings instance for FastAPI Dependency Injection."""
    return settings
