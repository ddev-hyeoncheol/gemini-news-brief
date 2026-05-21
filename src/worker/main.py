import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.config.config import settings
from src.core.logger import configure_uvicorn_loggers, get_logger
from src.core.middleware import trace_context_middleware
from src.providers.bigquery import BigQueryProvider
from src.providers.gemini import GeminiProvider
from src.worker.routers import ingest, refine

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage lifespan context for startup and shutdown events.
    This replaces the deprecated @app.on_event decorators.
    """
    configure_uvicorn_loggers()

    # Initialize shared resources on startup.
    # All semaphores are created here to ensure they are bound to the correct event loop.
    app.state.source_semaphore = asyncio.Semaphore(10)
    app.state.bigquery_provider = BigQueryProvider(semaphore=asyncio.Semaphore(10))
    app.state.gemini_provider = GeminiProvider(semaphore=asyncio.Semaphore(10))
    logger.info("App startup completed | app: worker")

    yield
    logger.info("App shutdown completed | app: worker")


app = FastAPI(title="Gemini News Brief Worker API", lifespan=lifespan)

app.middleware("http")(trace_context_middleware)

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
