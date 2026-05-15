import asyncio
import hashlib

from typing import Any

# TODO(refactor): TransformPlugin has grown complex.
# Consider splitting into SilverNewsTransformer and SilverNewsAugmentedTransformer
# to separate concerns between Pydantic transformation and LLM-based augmentation.
from src.core.logger import get_logger
from src.core.decorators import with_refine_error_handling
from src.models.entities.silver_news import SilverNewsModel
from src.models.entities.silver_news_augmented import SilverNewsAugmentedModel
from src.models.schemas.llm import LLMAnalysisResult
from src.models.schemas.refine import RefineRequest, RefineTransformResult
from src.providers.gemini import GeminiProvider
from src.worker.plugins.stores.silver import SilverStore

logger = get_logger(__name__)

_CHUNK_SIZE = 3


class TransformPlugin:
    """
    Plugin that orchestrates data transformation for the refinement pipeline.
    Handles data conversion and external AI model interactions.
    """

    def __init__(self, gemini_provider: GeminiProvider) -> None:
        """Initialize the plugin with an injected Gemini provider."""
        self.gemini = gemini_provider

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
            # CPU-bound Pydantic transformation.
            transformed_items = SilverNewsModel.from_bronze_news_list(items)

            logger.info(
                "[%s] Transform completed | count: %d",
                request.target_table,
                len(transformed_items),
            )
            return {"items": transformed_items}

        elif request.target_table == SilverStore._SILVER_NEWS_AUGMENTED:
            transformed_items = await self._transform_augmented(request, items)
            success_count = sum(
                1 for item in transformed_items if item.status == "success"
            )

            logger.info(
                "[%s] Transform completed | success: %d, total: %d",
                request.target_table,
                success_count,
                len(transformed_items),
            )

            # Signal partial when any item failed, so RefineService and the response reflect reality.
            # The load phase still runs to persist both success and failed records.
            if success_count < len(transformed_items):
                return {
                    "items": transformed_items,
                    "item_count": success_count,
                    "status": "partial",
                }
            return {"items": transformed_items, "item_count": success_count}

        return {"items": transformed_items}

    async def _transform_augmented(
        self, request: RefineRequest, items: list[SilverNewsModel]
    ) -> list[SilverNewsAugmentedModel]:
        """Split items into chunks and call the LLM provider in parallel, then map results."""
        # Sort by news_id for deterministic chunking — same inputs always produce the same batch_ids.
        sorted_items = sorted(items, key=lambda item: item.news_id)

        # Split into fixed-size chunks and call LLM concurrently.
        chunks = [
            sorted_items[i : i + _CHUNK_SIZE]
            for i in range(0, len(sorted_items), _CHUNK_SIZE)
        ]
        chunk_results = await asyncio.gather(
            *[self.gemini.generate_content(chunk) for chunk in chunks]
        )

        # Compute a batch_id per chunk by hashing the concatenated news_ids of that chunk.
        # Chunks are already in sorted order, so concatenation is deterministic.
        # Mirrors the news_id generation approach: sha256(raw_key).hexdigest().
        chunk_batch_ids = [
            hashlib.sha256("".join(item.news_id for item in chunk).encode()).hexdigest()
            for chunk in chunks
        ]

        # Build per-item lookups: news_id → batch_id, news_id → LLMAnalysisResult.
        # failed_ids tracks news_ids whose entire chunk failed (generate_result is None).
        item_batch_id: dict[str, str] = {}
        result_map: dict[str, LLMAnalysisResult] = {}
        failed_ids: set[str] = set()

        for chunk, generate_result, batch_id in zip(
            chunks, chunk_results, chunk_batch_ids
        ):
            for item in chunk:
                item_batch_id[item.news_id] = batch_id

            if generate_result is None:
                for item in chunk:
                    failed_ids.add(item.news_id)
                logger.warning(
                    "[%s] LLM chunk failed | news_ids: %s | batch_id: %s",
                    request.target_table,
                    [item.news_id for item in chunk],
                    batch_id,
                )
            else:
                for r in generate_result.results:
                    result_map[r.news_id] = r

        model_name = self.gemini.model_name
        model_version = self.gemini.model_version

        augmented: list[SilverNewsAugmentedModel] = []
        for item in items:
            batch_id = item_batch_id[item.news_id]

            if item.news_id in failed_ids:
                augmented.append(
                    SilverNewsAugmentedModel(
                        executed_at=request.executed_at,
                        news_id=item.news_id,
                        model=model_name,
                        version=model_version,
                        batch_id=batch_id,
                        status="failed",
                        error_message="LLM generation failed",
                    )
                )
                continue

            llm = result_map.get(item.news_id)
            if llm is None:
                logger.warning(
                    "[%s] LLM result missing | news_id: %s | batch_id: %s",
                    request.target_table,
                    item.news_id,
                    batch_id,
                )
                augmented.append(
                    SilverNewsAugmentedModel(
                        executed_at=request.executed_at,
                        news_id=item.news_id,
                        model=model_name,
                        version=model_version,
                        batch_id=batch_id,
                        status="failed",
                        error_message="LLM result not found",
                    )
                )
            else:
                augmented.append(
                    SilverNewsAugmentedModel(
                        executed_at=request.executed_at,
                        news_id=item.news_id,
                        model=model_name,
                        version=model_version,
                        ai_sector=llm.ai_sector,
                        ai_format=llm.ai_format,
                        ai_sentiment=llm.ai_sentiment,
                        ai_title=llm.ai_title,
                        ai_author=llm.ai_author,
                        ai_summary=llm.ai_summary,
                        ai_content_clean=llm.ai_content_clean,
                        batch_id=batch_id,
                        status="success",
                    )
                )

        return augmented
