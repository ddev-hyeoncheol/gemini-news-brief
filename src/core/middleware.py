from collections.abc import Awaitable, Callable

from fastapi import Request, Response

from src.core.request_context import (
    parse_cloud_trace_context,
    reset_trace_context,
    set_trace_context,
)


async def trace_context_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Bind Google Cloud trace context to application logs for a single request."""
    trace_id, span_id = parse_cloud_trace_context(
        request.headers.get("x-cloud-trace-context")
    )
    token = set_trace_context(trace_id=trace_id, span_id=span_id)

    try:
        return await call_next(request)
    finally:
        reset_trace_context(token)
