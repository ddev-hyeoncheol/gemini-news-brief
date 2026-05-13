from typing import Any

from src.core.logger import get_logger
from src.core.decorators import with_refine_error_handling
from src.models.entities.silver_news import SilverNewsModel
from src.models.schemas.refine import RefineRequest, RefineTransformResult
from src.worker.plugins.stores.silver import SilverStore

logger = get_logger(__name__)


class TransformPlugin:
    """
    Plugin that orchestrates data transformation for the refinement pipeline.
    Handles data conversion and external AI model interactions.
    """

    @with_refine_error_handling(RefineTransformResult)
    async def transform(
        self, request: RefineRequest, items: list[Any]
    ) -> dict[str, Any]:
        """Transform extracted items into the target schema."""
        if not items:
            logger.info(
                "[%s] Transform skipped | reason: no items", request.target_table
            )
            return {"items": []}

        transformed_items = []

        if request.target_table == SilverStore._SILVER_NEWS:
            # CPU-bound Pydantic transformation
            transformed_items = SilverNewsModel.from_bronze_news_list(items)
        elif request.target_table == SilverStore._SILVER_NEWS_AUGMENTED:
            # TODO: Implement LLM API integration for SilverNewsAugmentedModel
            transformed_items = []

        logger.info(
            "[%s] Transform completed | count: %d",
            request.target_table,
            len(transformed_items),
        )
        return {"items": transformed_items}
