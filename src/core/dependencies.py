import asyncio

from fastapi import Request

from src.providers.bigquery import BigQueryProvider
from src.providers.gemini import GeminiProvider


def get_source_semaphore(request: Request) -> asyncio.Semaphore:
    """
    Return the shared source collection semaphore from FastAPI app state.
    Limit concurrent outgoing web requests across source plugins.
    """
    return request.app.state.source_semaphore


def get_bigquery_provider(request: Request) -> BigQueryProvider:
    """Return the shared BigQueryProvider from FastAPI app state."""
    return request.app.state.bigquery_provider


def get_gemini_provider(request: Request) -> GeminiProvider:
    """Return the shared GeminiProvider from FastAPI app state."""
    return request.app.state.gemini_provider
