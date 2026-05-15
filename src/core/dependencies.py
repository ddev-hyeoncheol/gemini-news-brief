from fastapi import Request

from src.providers.bigquery import BigQueryProvider


def get_bq_provider(request: Request) -> BigQueryProvider:
    """
    Retrieve the BigQueryProvider instance from the FastAPI application state.
    This serves as a bridge between the framework's state and the application logic.
    """
    return request.app.state.bq_provider
