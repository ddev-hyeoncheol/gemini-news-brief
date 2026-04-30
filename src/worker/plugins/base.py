from abc import ABC, abstractmethod
from typing import Any


class BasePlugin(ABC):
    """Abstract base class for all worker plugins."""

    @abstractmethod
    async def execute(self, *args: Any, **kwargs: Any) -> Any:
        """Main entry point for executing the plugin."""
        ...
