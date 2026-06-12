import asyncio
import uuid
from datetime import datetime

from google.genai import types
from pydantic import TypeAdapter

from src.core.logger import get_logger
from src.models.entities.silver_news import SilverNewsModel
from src.models.entities.silver_news_augmented import SilverNewsAugmentedModel
from src.models.schemas.llm import LLMNewsAugmentedResult
from src.providers.gemini import GeminiProvider
from src.worker.plugins.prompts.news_augmented import (
    ANALYSIS_VERSION,
    DEFAULT_GENERATE_CONTENT_CONFIG,
    NEWS_ITEM_PROMPT_TEMPLATE,
)

logger = get_logger(__name__)


_NAMESPACE_UUID = uuid.uuid5(uuid.NAMESPACE_DNS, "gemini-news-brief")

_CHUNK_SIZE = 3
_AUGMENTED_RESULT_FIELDS = {
    "ai_category",
    "ai_format",
    "ai_sentiment",
    "ai_market_entities",
    "ai_authors",
    "ai_content",
    "ai_title_ko",
    "ai_summary_ko",
    "ai_summary_bullets_ko",
    "ai_content_ko",
}
_RESULT_ADAPTER = TypeAdapter(list[LLMNewsAugmentedResult])


class AiPlugin:
    """
    Plugin that transforms Silver news into AI-augmented records using an LLM.
    Coordinates Gemini requests, deterministic chunking, and result alignment.
    """

    def __init__(self, gemini_provider: GeminiProvider) -> None:
        """Initialize the plugin with an injected Gemini provider."""
        self._gemini = gemini_provider

    async def run_transform_silver_news_augmented(
        self,
        executed_at: datetime,
        items: list[SilverNewsModel],
    ) -> list[SilverNewsAugmentedModel]:
        """Transform Silver news items into AI-augmented news items."""
        if not items:
            logger.info("AiPlugin transform_silver_news_augmented skipped | reason: no items")
            return []

        if not self._gemini.is_available:
            logger.warning(
                "AiPlugin transform_silver_news_augmented failed | reason: llm provider unavailable, count: %d",
                len(items),
            )
            transformed_items = [
                self._create_failed_silver_news_augmented_model(
                    executed_at=executed_at,
                    item=item,
                    batch_id=None,
                    error_message="LLM provider unavailable",
                )
                for item in items
            ]
        else:
            transformed_items = await self._transform_items(executed_at, items)

        success_count = sum(1 for item in transformed_items if item.status == "success")
        failed_count = len(transformed_items) - success_count

        logger.info(
            "AiPlugin transform_silver_news_augmented completed | count: %d, success_count: %d, failed_count: %d",
            len(transformed_items),
            success_count,
            failed_count,
        )

        return transformed_items

    async def _transform_items(
        self,
        executed_at: datetime,
        items: list[SilverNewsModel],
    ) -> list[SilverNewsAugmentedModel]:
        """Split items into deterministic chunks and transform each chunk."""
        chunks = self._chunk_items(items)
        chunk_results = await asyncio.gather(*(self._transform_chunk(executed_at, chunk) for chunk in chunks))
        return [model for chunk_result in chunk_results for model in chunk_result]

    async def _transform_chunk(
        self,
        executed_at: datetime,
        chunk: list[SilverNewsModel],
    ) -> list[SilverNewsAugmentedModel]:
        """Transform one deterministic LLM chunk into augmented news records."""
        batch_id = self._make_chunk_batch_id(chunk)

        try:
            contents = self._serialize_chunk(chunk)
            response = await self._gemini.generate_content(
                contents=contents,
                config=DEFAULT_GENERATE_CONTENT_CONFIG,
            )
            result_map = self._map_chunk_results(
                chunk=chunk,
                batch_id=batch_id,
                parsed_results=self._parse_generate_response(response),
            )
        except Exception as e:
            logger.warning(
                "AiPlugin transform_silver_news_augmented chunk failed | "
                "batch_id: %s, reason: chunk generation failed, error: %s",
                batch_id,
                str(e),
            )
            return [
                self._create_failed_silver_news_augmented_model(
                    executed_at=executed_at,
                    item=item,
                    batch_id=batch_id,
                    error_message="Chunk generation failed",
                )
                for item in chunk
            ]

        return [
            (
                self._create_success_silver_news_augmented_model(
                    executed_at=executed_at,
                    item=item,
                    batch_id=batch_id,
                    llm=llm,
                )
                if (llm := result_map.get(item.news_id)) is not None
                else self._create_failed_silver_news_augmented_model(
                    executed_at=executed_at,
                    item=item,
                    batch_id=batch_id,
                    error_message="LLM result not found",
                )
            )
            for item in chunk
        ]

    def _chunk_items(self, items: list[SilverNewsModel]) -> list[list[SilverNewsModel]]:
        """Return deterministic fixed-size chunks for LLM batch generation."""
        sorted_items = sorted(items, key=lambda item: item.news_id)
        return [sorted_items[i : i + _CHUNK_SIZE] for i in range(0, len(sorted_items), _CHUNK_SIZE)]

    def _make_chunk_batch_id(self, chunk: list[SilverNewsModel]) -> str:
        """Return a deterministic batch identifier for one LLM chunk."""
        raw_key = "\n".join(item.news_id for item in chunk)
        return str(uuid.uuid5(_NAMESPACE_UUID, raw_key))

    def _serialize_chunk(self, items: list[SilverNewsModel]) -> str:
        """Concatenate all news prompts into a single batch request string."""
        return "\n".join(
            NEWS_ITEM_PROMPT_TEMPLATE.format(
                news_id=item.news_id,
                source=item.source,
                title=item.title,
                url=item.url,
                published_at=item.published_at.isoformat(),
                language=item.language or "",
                raw_authors=item.raw_authors or "",
                raw_content=item.raw_content,
            )
            for item in items
        )

    def _parse_generate_response(self, response: types.GenerateContentResponse) -> list[LLMNewsAugmentedResult]:
        """Parse Gemini JSON output into validated news augmentation results."""
        text = response.text

        if not text:
            raise ValueError("Gemini response text is empty or None")
        return _RESULT_ADAPTER.validate_json(text)

    def _map_chunk_results(
        self,
        chunk: list[SilverNewsModel],
        batch_id: str,
        parsed_results: list[LLMNewsAugmentedResult],
    ) -> dict[str, LLMNewsAugmentedResult]:
        """Return parsed LLM results keyed by news_id for one chunk."""
        chunk_news_ids = {item.news_id for item in chunk}
        result_map = {result.news_id: result for result in parsed_results if result.news_id in chunk_news_ids}
        missing_count = len(chunk_news_ids - result_map.keys())
        ignored_count = sum(1 for result in parsed_results if result.news_id not in chunk_news_ids)

        if missing_count or ignored_count:
            logger.warning(
                "AiPlugin transform_silver_news_augmented result_mismatch detected | "
                "batch_id: %s, missing_count: %d, ignored_count: %d",
                batch_id,
                missing_count,
                ignored_count,
            )

        return result_map

    def _create_failed_silver_news_augmented_model(
        self,
        executed_at: datetime,
        item: SilverNewsModel,
        batch_id: str | None,
        error_message: str | None,
    ) -> SilverNewsAugmentedModel:
        """Return a failed augmented news record for one Silver news item."""
        return SilverNewsAugmentedModel(
            executed_at=executed_at,
            news_id=item.news_id,
            model_provider=self._gemini.MODEL_PROVIDER,
            model_name=self._gemini.MODEL_NAME,
            analysis_version=ANALYSIS_VERSION,
            batch_id=batch_id,
            status="failed",
            error_message=error_message,
        )

    def _create_success_silver_news_augmented_model(
        self,
        executed_at: datetime,
        item: SilverNewsModel,
        batch_id: str,
        llm: LLMNewsAugmentedResult,
    ) -> SilverNewsAugmentedModel:
        """Return a successful augmented news record from one LLM result."""
        llm_fields = llm.model_dump(include=_AUGMENTED_RESULT_FIELDS)

        return SilverNewsAugmentedModel(
            executed_at=executed_at,
            news_id=item.news_id,
            model_provider=self._gemini.MODEL_PROVIDER,
            model_name=self._gemini.MODEL_NAME,
            analysis_version=ANALYSIS_VERSION,
            batch_id=batch_id,
            status="success",
            **llm_fields,
        )
