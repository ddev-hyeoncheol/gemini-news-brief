import os
import asyncio

from fastapi import FastAPI
from contextlib import asynccontextmanager

from src.core.logger import configure_uvicorn_loggers, get_logger
from src.core.bigquery import get_bigquery_client
from src.worker.routers import ingest

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage lifespan context for startup and shutdown events.
    This replaces the deprecated @app.on_event decorators.
    """
    configure_uvicorn_loggers()
    logger.info("Gemini News Brief Worker API Started")

    # Initialize shared resources (semaphores and DB client) on startup.
    app.state.source_semaphore = asyncio.Semaphore(10)
    app.state.db_semaphore = asyncio.Semaphore(10)
    app.state.bigquery_client = get_bigquery_client()

    yield
    logger.info("Gemini News Brief Worker API Shutdown")


app = FastAPI(title="Gemini News Brief Worker API", lifespan=lifespan)

app.include_router(ingest.router)


@app.get("/")
async def root():
    """Return a welcome message."""
    return {"message": "Welcome to Gemini News Brief Worker API"}


@app.get("/health")
async def health_check():
    """Return health status for Cloud Run and Load Balancers to verify service availability."""
    return {"status": "health", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn

    # Cloud Run injects the PORT environment variable dynamically. Fallback to 8080 for local development.
    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run("src.worker.main:app", host="0.0.0.0", port=port, reload=False)
