from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.config.config import settings
from src.core.logger import configure_uvicorn_loggers, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage API application startup and shutdown."""
    configure_uvicorn_loggers()

    logger.info("App startup completed | app: api")
    yield
    logger.info("App shutdown completed | app: api")


app = FastAPI(title="Gemini News Brief API App", lifespan=lifespan)


@app.get("/")
async def root():
    """Return the welcome message."""
    return {"message": "Welcome to Gemini News Brief API App"}


@app.get("/health")
async def health_check():
    """Return health status for Cloud Run and Load Balancers to verify service availability."""
    return {"status": "healthy", "version": "1.0.0"}


def run_app() -> None:
    """Run the API application with configured runtime settings."""
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=not settings.is_gcp,
    )


if __name__ == "__main__":
    run_app()
