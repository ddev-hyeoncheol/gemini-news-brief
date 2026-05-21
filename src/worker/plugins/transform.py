import asyncio
import hashlib
from typing import Any

from src.core.decorators import with_refine_error_handling
from src.core.logger import get_logger
from src.models.entities.bronze_news import BronzeNewsModel
from src.models.entities.silver_news import SilverNewsModel
from src.models.entities.silver_news_augmented import SilverNewsAugmentedModel
from src.models.schemas.llm import LLMAnalysisResult, LLMGenerateResult
from src.models.schemas.refine import RefineRequest, RefineTransformResult
from src.providers.gemini import GeminiProvider

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
    async def transform_silver_news(
        self, request: RefineRequest, items: list[BronzeNewsModel]
    ) -> dict[str, Any]:
        """Transform Bronze news items into Silver news items."""
        if not items:
            logger.info("Plugin transform skipped | target: news, reason: no items")
            return {"items": []}

        transformed_items = SilverNewsModel.from_bronze_news_list(items)

        logger.info(
            "Plugin transform completed | target: news, count: %d",
            len(transformed_items),
        )
        return {"items": transformed_items}

    @with_refine_error_handling(RefineTransformResult)
    async def transform_silver_news_augmented(
        self, request: RefineRequest, items: list[SilverNewsModel]
    ) -> dict[str, Any]:
        """Transform Silver news items into AI-augmented news items."""
        if not items:
            logger.info(
                "Plugin transform skipped | target: news-augmented, reason: no items"
            )
            return {"items": []}

        transformed_items = await self._transform_silver_news_augmented(request, items)
        success_count = sum(1 for item in transformed_items if item.status == "success")

        logger.info(
            "Plugin transform completed | target: news-augmented, count: %d, total: %d",
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

    async def _transform_silver_news_augmented(
        self, request: RefineRequest, items: list[SilverNewsModel]
    ) -> list[SilverNewsAugmentedModel]:
        """Split items into chunks and call the LLM provider in parallel, then map results."""
        chunks = self._chunk_silver_news(items)
        chunk_results = await self._generate_llm_results(chunks)
        chunk_batch_ids = [self._make_chunk_batch_id(chunk) for chunk in chunks]
        item_batch_id, result_map, failed_ids = self._map_silver_news_augmented_results(
            chunks=chunks,
            chunk_results=chunk_results,
            chunk_batch_ids=chunk_batch_ids,
        )

        return [
            self._create_silver_news_augmented_model(
                request=request,
                item=item,
                batch_id=item_batch_id[item.news_id],
                llm=result_map.get(item.news_id),
                failed=item.news_id in failed_ids,
            )
            for item in items
        ]

    def _chunk_silver_news(
        self, items: list[SilverNewsModel]
    ) -> list[list[SilverNewsModel]]:
        """Return deterministic fixed-size chunks for LLM batch generation."""
        sorted_items = sorted(items, key=lambda item: item.news_id)
        return [
            sorted_items[i : i + _CHUNK_SIZE]
            for i in range(0, len(sorted_items), _CHUNK_SIZE)
        ]

    async def _generate_llm_results(
        self, chunks: list[list[SilverNewsModel]]
    ) -> list[LLMGenerateResult | None]:
        """Generate LLM results for all chunks concurrently."""
        return await asyncio.gather(
            *[self.gemini.generate_content(chunk) for chunk in chunks]
        )

    def _make_chunk_batch_id(self, chunk: list[SilverNewsModel]) -> str:
        """Return a deterministic batch identifier for a chunk."""
        raw_key = "".join(item.news_id for item in chunk)
        return hashlib.sha256(raw_key.encode()).hexdigest()

    def _map_silver_news_augmented_results(
        self,
        chunks: list[list[SilverNewsModel]],
        chunk_results: list[LLMGenerateResult | None],
        chunk_batch_ids: list[str],
    ) -> tuple[dict[str, str], dict[str, LLMAnalysisResult], set[str]]:
        """Return lookup maps for batch identifiers, LLM results, and failed items."""
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
                    "Plugin transform chunk failed | target: news-augmented, batch_id: %s, news_ids: %s, reason: llm generation failed",
                    batch_id,
                    [item.news_id for item in chunk],
                )
            else:
                chunk_news_ids = {item.news_id for item in chunk}
                for r in generate_result.results:
                    if r.news_id not in chunk_news_ids:
                        logger.warning(
                            "Plugin transform item ignored | target: news-augmented, news_id: %s, batch_id: %s, reason: llm result outside chunk",
                            r.news_id,
                            batch_id,
                        )
                        continue
                    result_map[r.news_id] = r

        return item_batch_id, result_map, failed_ids

    def _create_silver_news_augmented_model(
        self,
        request: RefineRequest,
        item: SilverNewsModel,
        batch_id: str,
        llm: LLMAnalysisResult | None,
        failed: bool,
    ) -> SilverNewsAugmentedModel:
        """Return an augmented news record from an LLM result or failure state."""
        if failed:
            return self._create_failed_silver_news_augmented_model(
                request=request,
                item=item,
                batch_id=batch_id,
                error_message="LLM generation failed",
            )

        if llm is None:
            logger.warning(
                "Plugin transform item failed | target: news-augmented, news_id: %s, batch_id: %s, reason: llm result missing",
                item.news_id,
                batch_id,
            )
            return self._create_failed_silver_news_augmented_model(
                request=request,
                item=item,
                batch_id=batch_id,
                error_message="LLM result not found",
            )

        return SilverNewsAugmentedModel(
            executed_at=request.executed_at,
            news_id=item.news_id,
            model=self.gemini.model_name,
            version=self.gemini.model_version,
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

    def _create_failed_silver_news_augmented_model(
        self,
        request: RefineRequest,
        item: SilverNewsModel,
        batch_id: str,
        error_message: str,
    ) -> SilverNewsAugmentedModel:
        """Return a failed augmented news record."""
        return SilverNewsAugmentedModel(
            executed_at=request.executed_at,
            news_id=item.news_id,
            model=self.gemini.model_name,
            version=self.gemini.model_version,
            batch_id=batch_id,
            status="failed",
            error_message=error_message,
        )
