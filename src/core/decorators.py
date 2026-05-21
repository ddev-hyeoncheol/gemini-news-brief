import functools
from collections.abc import Callable, Coroutine
from datetime import datetime, timezone
from typing import Any, TypeVar

from src.core.logger import get_logger
from src.models.schemas.ingest import IngestPhaseResultBase
from src.models.schemas.refine import RefinePhaseResultBase

logger = get_logger(__name__)

T = TypeVar("T", bound=IngestPhaseResultBase)
R = TypeVar("R", bound=RefinePhaseResultBase)


def with_ingest_error_handling(
    dto_class: type[T],
) -> Callable[
    [Callable[..., Coroutine[Any, Any, dict[str, Any]]]],
    Callable[..., Coroutine[Any, Any, T]],
]:
    """
    Wrap an ingest plugin phase and return an ingest phase result DTO.

    The wrapped method must return DTO field values as a dictionary.
    The plugin or call arguments must provide a source string before phase execution.
    Exceptions raised by the wrapped method are converted into failed phase results.
    """

    def decorator(
        func: Callable[..., Coroutine[Any, Any, dict[str, Any]]],
    ) -> Callable[..., Coroutine[Any, Any, T]]:
        @functools.wraps(func)
        async def wrapper(self: Any, *args: Any, **kwargs: Any) -> T:
            started_at = datetime.now(tz=timezone.utc)
            source = _get_ingest_source(self, args, kwargs)
            operation = _get_plugin_operation(func.__name__)

            try:
                result_data = await func(self, *args, **kwargs)

                # Allow inner function to explicitly set status (e.g., "partial"), otherwise default to "success".
                status = result_data.pop("status", "success")
                result_data["source"] = source

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
                    "Plugin %s failed | source: %s, method: %s",
                    operation,
                    source,
                    func.__name__,
                )
                return dto_class(
                    source=source,
                    status="failed",
                    started_at=started_at,
                    completed_at=datetime.now(tz=timezone.utc),
                    error_message=f"{type(e).__name__}::{e}",
                )

        return wrapper

    return decorator


def with_refine_error_handling(
    dto_class: type[R],
) -> Callable[
    [Callable[..., Coroutine[Any, Any, dict[str, Any]]]],
    Callable[..., Coroutine[Any, Any, R]],
]:
    """
    Wrap a refine plugin phase and return a refine phase result DTO.

    The wrapped method must return DTO field values as a dictionary.
    Exceptions raised by the wrapped method are converted into failed phase results.
    """

    def decorator(
        func: Callable[..., Coroutine[Any, Any, dict[str, Any]]],
    ) -> Callable[..., Coroutine[Any, Any, R]]:
        @functools.wraps(func)
        async def wrapper(self: Any, *args: Any, **kwargs: Any) -> R:
            started_at = datetime.now(tz=timezone.utc)
            operation = _get_plugin_operation(func.__name__)

            try:
                result_data = await func(self, *args, **kwargs)

                status = result_data.pop("status", "success")

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
                    "Plugin %s failed | method: %s",
                    operation,
                    func.__name__,
                )
                return dto_class(
                    status="failed",
                    started_at=started_at,
                    completed_at=datetime.now(tz=timezone.utc),
                    error_message=f"{type(e).__name__}::{e}",
                )

        return wrapper

    return decorator


def _get_ingest_source(self: Any, args: tuple[Any, ...], kwargs: dict[str, Any]) -> str:
    """Return the ingest source string from the plugin instance or call arguments."""
    source = getattr(self, "source", None)
    if isinstance(source, str):
        return source

    source = kwargs.get("source")
    if isinstance(source, str):
        return source

    if args and isinstance(args[0], str):
        return args[0]

    raise ValueError("source must be provided for ingest phase result.")


def _get_plugin_operation(method_name: str) -> str:
    """Return the log operation prefix from a plugin method name."""
    return method_name.split("_", maxsplit=1)[0]
