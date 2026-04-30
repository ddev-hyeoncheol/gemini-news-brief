import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.core.logger import configure_uvicorn_loggers, get_logger
from src.worker.routers import ingest

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    This replaces the deprecated @app.on_event decorators.
    """
    configure_uvicorn_loggers()
    logger.info("Gemini News Brief Worker API Started")
    yield
    logger.info("Gemini News Brief Worker API Shutdown")


app = FastAPI(title="Gemini News Brief Worker API", lifespan=lifespan)

app.include_router(ingest.router)


@app.get("/")
async def root():
    """Root endpoint returning a welcome message."""
    return {"message": "Welcome to Gemini News Brief Worker API"}


@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run and Load Balancers to verify service availability."""
    return {"status": "health", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn

    # Cloud Run injects the PORT environment variable dynamically. Fallback to 8080 for local development.
    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run("src.worker.main:app", host="0.0.0.0", port=port, reload=False)
