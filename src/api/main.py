from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.config.config import settings
from src.core.logger import configure_uvicorn_loggers, get_logger
from src.core.middleware import trace_context_middleware

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage API application startup and shutdown."""
    configure_uvicorn_loggers()

    logger.info("App startup completed | app: api")
    yield
    logger.info("App shutdown completed | app: api")


app = FastAPI(title="Gemini News Brief API", lifespan=lifespan)

app.middleware("http")(trace_context_middleware)


@app.get("/")
async def root():
    """Return the welcome message."""
    return {"message": "Welcome to Gemini News Brief API"}


@app.get("/health")
async def health_check():
    """Return health status for Cloud Run and Load Balancers to verify service availability."""
    return {"status": "health", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.api.main:app", host="0.0.0.0", port=settings.port, reload=False)
