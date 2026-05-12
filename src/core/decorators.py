import functools
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, TypeVar

from src.core.logger import get_logger
from src.models.schemas.ingest import IngestPhaseResultBase

logger = get_logger(__name__)

T = TypeVar("T", bound=IngestPhaseResultBase)


def with_ingest_error_handling(
    dto_class: type[T],
) -> Callable[
    [Callable[..., Coroutine[Any, Any, dict[str, Any]]]],
    Callable[..., Coroutine[Any, Any, T]],
]:
    """
    Decorate ingest pipeline plugin methods to handle boilerplate:
    1. Time tracking (started_at, completed_at)
    2. Error isolation and logging
    3. DTO instantiation mapping

    The decorated async function must return a dictionary of fields.
    If the dictionary contains a 'status' key (e.g., 'partial'), it overrides the default 'success'.
    """

    def decorator(
        func: Callable[..., Coroutine[Any, Any, dict[str, Any]]],
    ) -> Callable[..., Coroutine[Any, Any, T]]:
        @functools.wraps(func)
        async def wrapper(self: Any, *args: Any, **kwargs: Any) -> T:
            started_at = datetime.now(tz=timezone.utc)

            # Extract 'source' dynamically based on different plugin patterns.
            # Prefer an explicit 'source_name' property (e.g., CollectPlugin),
            # then fall back to the first positional string argument (e.g., IngestDbPlugin).
            source_name = "unknown"
            if hasattr(self, "source_name"):
                source_name = self.source_name
            elif args and isinstance(args[0], str):
                source_name = args[0]

            try:
                result_data = await func(self, *args, **kwargs)

                # Allow inner function to explicitly set status (e.g., "partial"), otherwise default to "success".
                status = result_data.pop("status", "success")
                if "source" not in result_data:
                    result_data["source"] = source_name

                # Auto-calculate item_count if items are provided but item_count is omitted.
                if "items" in result_data and "item_count" not in result_data:
                    result_data["item_count"] = len(result_data["items"])

                return dto_class(
                    status=status,
                    started_at=started_at,
                    completed_at=datetime.now(tz=timezone.utc),
                    **result_data,
                )
            except Exception as e:
                logger.exception(
                    "Phase failed | source: %s, phase: %s",
                    source_name,
                    func.__name__,
                )
                return dto_class(
                    source=source_name,
                    status="failed",
                    started_at=started_at,
                    completed_at=datetime.now(tz=timezone.utc),
                    error_message=f"{type(e).__name__}::{e}",
                )

        return wrapper

    return decorator
