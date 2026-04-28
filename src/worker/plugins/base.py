from abc import ABC, abstractmethod


class BasePlugin(ABC):
    """Abstract base class for all worker plugins."""

    @abstractmethod
    async def execute(self, *args, **kwargs):
        """Main entry point for executing the plugin."""
        ...
