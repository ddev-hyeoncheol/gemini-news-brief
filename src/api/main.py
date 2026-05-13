from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.config.config import settings
from src.core.logger import configure_uvicorn_loggers, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_uvicorn_loggers()
    logger.info("Gemini News Brief API Started")
    yield
    logger.info("Gemini News Brief API Shutdown")


app = FastAPI(title="Gemini News Brief API", lifespan=lifespan)


@app.get("/")
async def root():
    return {"message": "Welcome to Gemini News Brief API"}


@app.get("/health")
async def health_check():
    return {"status": "health", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.api.main:app", host="0.0.0.0", port=settings.port, reload=False)
