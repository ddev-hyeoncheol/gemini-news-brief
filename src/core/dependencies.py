import asyncio

from fastapi import Request

from src.providers.bigquery import BigQueryProvider
from src.providers.gemini import GeminiProvider


def get_source_semaphore(request: Request) -> asyncio.Semaphore:
    """
    Retrieve the shared source collection semaphore from the FastAPI application state.
    Throttle concurrent outgoing web requests.
    """
    return request.app.state.source_semaphore


def get_bigquery_provider(request: Request) -> BigQueryProvider:
    """
    Retrieve the BigQueryProvider instance from the FastAPI application state.
    This serves as a bridge between the framework's state and the application logic.
    """
    return request.app.state.bigquery_provider


def get_gemini_provider(request: Request) -> GeminiProvider:
    """
    Retrieve the GeminiProvider instance from the FastAPI application state.
    This serves as a bridge between the framework's state and the application logic.
    """
    return request.app.state.gemini_provider
