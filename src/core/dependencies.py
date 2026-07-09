import asyncio

from fastapi import Request


def get_source_semaphore(request: Request) -> asyncio.Semaphore:
    """
    Return the shared source collection semaphore from FastAPI app state.
    Limit concurrent outgoing web requests across source plugins.
    """
    return request.app.state.source_semaphore
