import asyncio

from fastapi import FastAPI
from contextlib import asynccontextmanager

from src.config.config import settings
from src.core.logger import configure_uvicorn_loggers, get_logger
from src.providers.bigquery import BigQueryProvider
from src.worker.routers import ingest, refine

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage lifespan context for startup and shutdown events.
    This replaces the deprecated @app.on_event decorators.
    """
    configure_uvicorn_loggers()
    logger.info("Gemini News Brief Worker API Started")

    # Initialize shared resources on startup.
    app.state.bq_provider = BigQueryProvider(semaphore_limit=10)
    app.state.source_semaphore = asyncio.Semaphore(10)

    yield
    logger.info("Gemini News Brief Worker API Shutdown")


app = FastAPI(title="Gemini News Brief Worker API", lifespan=lifespan)

app.include_router(ingest.router)
app.include_router(refine.router)


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

    uvicorn.run("src.worker.main:app", host="0.0.0.0", port=settings.port, reload=False)
