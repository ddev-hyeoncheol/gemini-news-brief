from datetime import datetime, timezone
from typing import Literal
from fastapi import Request

from src.core.logger import get_logger
from src.models.schemas.refine import RefineRequest, RefineResponse
from src.worker.plugins.bigquery import RefineDbPlugin
from src.worker.plugins.transform import TransformPlugin
from src.worker.plugins.stores.silver import SilverStore

logger = get_logger(__name__)


class RefineService:
    """Orchestrate the refinement pipeline (extract -> transform -> load) for a single target."""

    def __init__(
        self, db_plugin: RefineDbPlugin, transform_plugin: TransformPlugin
    ) -> None:
        """Initialize the service with required plugins."""
        self.db_plugin = db_plugin
        self.transform_plugin = transform_plugin

    async def run(self, request: RefineRequest) -> RefineResponse:
        """Run the refinement pipeline sequentially and return the aggregate result."""
        started_at = datetime.now(tz=timezone.utc)

        # 1. Extract phase.
        extract_res = await self.db_plugin.extract(request)
        if extract_res.status == "failed":
            return self._create_failed_response(
                request=request,
                started_at=started_at,
                failed_phase="extract",
                error_message=extract_res.error_message,
            )

        # 2. Transform phase.
        transform_res = await self.transform_plugin.transform(
            request, extract_res.items
        )
        if transform_res.status == "failed":
            return self._create_failed_response(
                request=request,
                extracted_count=extract_res.item_count,
                started_at=started_at,
                failed_phase="transform",
                error_message=transform_res.error_message,
            )

        # 3. Load phase.
        load_res = await self.db_plugin.load(request, transform_res.items)
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
            target_table=request.target_table,
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
            target_table=request.target_table,
            status="failed",
            extracted_count=extracted_count,
            transformed_count=transformed_count,
            loaded_count=0,
            started_at=started_at,
            completed_at=datetime.now(tz=timezone.utc),
            failed_phase=failed_phase,
            error_message=error_message,
        )


def get_refine_service(request: Request) -> RefineService:
    """Provide FastAPI dependency for RefineService."""
    return RefineService(
        db_plugin=RefineDbPlugin(
            store=SilverStore(
                client=request.app.state.bigquery_client,
                semaphore=request.app.state.db_semaphore,
            )
        ),
        transform_plugin=TransformPlugin(),
    )
