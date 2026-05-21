from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings mapped from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Cloud Run injects the PORT environment variable dynamically. Fallback to 8080.
    port: int = 8080
    log_level: str = "INFO"

    # Cloud Run automatically sets K_SERVICE; use it to detect GCP environment.
    k_service: str | None = None

    # GCP Credentials for local development or explicit service account.
    google_application_credentials: str | None = None
    google_cloud_project: str | None = None
    gcp_project: str | None = None

    # Gemini API Keys (Injected via .env locally, or GCP Secret Manager in Cloud Run)
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
