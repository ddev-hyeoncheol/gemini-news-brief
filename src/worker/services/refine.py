from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import Depends

from src.core.dependencies import get_bigquery_provider, get_gemini_provider
from src.models.schemas.refine import (
    RefineExtractResult,
    RefineLoadResult,
    RefineRequest,
    RefineResponse,
    RefineTarget,
    RefineTransformResult,
)
from src.providers.bigquery import BigQueryProvider
from src.providers.gemini import GeminiProvider
from src.worker.plugins.bigquery import RefineDbPlugin
from src.worker.plugins.stores.silver import SilverStore
from src.worker.plugins.transform import TransformPlugin


@dataclass(frozen=True)
class RefinePipeline:
    """Connect target-specific refine phase handlers."""

    extract: Callable[[RefineRequest], Awaitable[RefineExtractResult[Any]]]
    transform: Callable[
        [RefineRequest, list[Any]], Awaitable[RefineTransformResult[Any]]
    ]
    load: Callable[[RefineRequest, list[Any]], Awaitable[RefineLoadResult[Any]]]


class RefineService:
    """Orchestrate the refinement pipeline (extract -> transform -> load) for a single target."""

    def __init__(
        self, db_plugin: RefineDbPlugin, transform_plugin: TransformPlugin
    ) -> None:
        """Initialize the service with required plugins."""
        self.db_plugin = db_plugin
        self.transform_plugin = transform_plugin
        self.registry: dict[RefineTarget, RefinePipeline] = {
            RefineTarget.NEWS: RefinePipeline(
                extract=self.db_plugin.extract_bronze_news,
                transform=self.transform_plugin.transform_silver_news,
                load=self.db_plugin.load_silver_news,
            ),
            RefineTarget.NEWS_AUGMENTED: RefinePipeline(
                extract=self.db_plugin.extract_silver_news,
                transform=self.transform_plugin.transform_silver_news_augmented,
                load=self.db_plugin.load_silver_news_augmented,
            ),
        }

    async def run(self, target: RefineTarget, request: RefineRequest) -> RefineResponse:
        """Run the refinement pipeline sequentially and return the aggregate result."""
        started_at = datetime.now(tz=timezone.utc)
        pipeline = self.registry[target]

        # 1. Extract phase.
        extract_res = await pipeline.extract(request)
        if extract_res.status == "failed":
            return self._create_failed_response(
                request=request,
                started_at=started_at,
                failed_phase="extract",
                error_message=extract_res.error_message,
            )

        # 2. Transform phase.
        transform_res = await pipeline.transform(request, extract_res.items)
        if transform_res.status == "failed":
            return self._create_failed_response(
                request=request,
                extracted_count=extract_res.item_count,
                started_at=started_at,
                failed_phase="transform",
                error_message=transform_res.error_message,
            )

        # 3. Load phase.
        load_res = await pipeline.load(request, transform_res.items)
        if load_res.status == "failed":
            return self._create_failed_response(
                request=request,
                extracted_count=extract_res.item_count,
                transformed_count=transform_res.item_count,
                started_at=started_at,
                failed_phase="load",
                error_message=load_res.error_message,
            )

        # Bubble up partial success and error message if transform was partial.
        # (If execution reaches here, load_res.status is guaranteed to be "success")
        status = "partial" if transform_res.status == "partial" else "success"

        return RefineResponse(
            executed_at=request.executed_at,
            status=status,
            extracted_count=extract_res.item_count,
            transformed_count=transform_res.item_count,
            loaded_count=load_res.item_count,
            started_at=started_at,
            completed_at=datetime.now(tz=timezone.utc),
            error_message=transform_res.error_message,
        )

    def _create_failed_response(
        self,
        request: RefineRequest,
        *,
        extracted_count: int = 0,
        transformed_count: int = 0,
        started_at: datetime,
        failed_phase: Literal["extract", "transform", "load"],
        error_message: str | None,
    ) -> RefineResponse:
        """Construct and return a failed RefineResponse."""
        return RefineResponse(
            executed_at=request.executed_at,
            status="failed",
            extracted_count=extracted_count,
            transformed_count=transformed_count,
            loaded_count=0,
            started_at=started_at,
            completed_at=datetime.now(tz=timezone.utc),
            failed_phase=failed_phase,
            error_message=error_message,
        )


def get_refine_service(
    bigquery_provider: BigQueryProvider = Depends(get_bigquery_provider),
    gemini_provider: GeminiProvider = Depends(get_gemini_provider),
) -> RefineService:
    """Provide FastAPI dependency for RefineService."""
    return RefineService(
        db_plugin=RefineDbPlugin(
            store=SilverStore(bigquery_provider=bigquery_provider)
        ),
        transform_plugin=TransformPlugin(gemini_provider=gemini_provider),
    )
