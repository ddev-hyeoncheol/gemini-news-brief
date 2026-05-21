from contextvars import ContextVar, Token
from dataclasses import dataclass

from src.config.config import settings

_gcp_trace: ContextVar[str | None] = ContextVar("gcp_trace", default=None)
_span_id: ContextVar[str | None] = ContextVar("span_id", default=None)


@dataclass(frozen=True)
class TraceContextToken:
    """Hold context variable tokens for request trace context reset."""

    gcp_trace: Token[str | None]
    span_id: Token[str | None]


def parse_cloud_trace_context(header: str | None) -> tuple[str | None, str | None]:
    """Parse an X-Cloud-Trace-Context header into trace and span identifiers."""
    if not header:
        return None, None

    trace_context = header.split(";", maxsplit=1)[0]
    trace_id, separator, span_id = trace_context.partition("/")
    if not trace_id:
        return None, None

    return trace_id, span_id if separator and span_id else None


def set_trace_context(trace_id: str | None, span_id: str | None) -> TraceContextToken:
    """Store request trace context for the current async execution context."""
    gcp_trace = (
        f"projects/{settings.gcp_project_id}/traces/{trace_id}"
        if settings.gcp_project_id and trace_id
        else None
    )

    return TraceContextToken(
        gcp_trace=_gcp_trace.set(gcp_trace),
        span_id=_span_id.set(span_id),
    )


def reset_trace_context(token: TraceContextToken) -> None:
    """Reset request trace context for the current async execution context."""
    _gcp_trace.reset(token.gcp_trace)
    _span_id.reset(token.span_id)


def get_gcp_trace() -> str | None:
    """Return the full GCP trace resource name for Cloud Logging correlation."""
    return _gcp_trace.get()


def get_span_id() -> str | None:
    """Return the current request span identifier if available."""
    return _span_id.get()
