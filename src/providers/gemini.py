import asyncio

import httpx
from google import genai
from google.genai import errors
from google.genai import types
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from src.config.config import settings
from src.core.logger import get_logger
from src.core.transient import is_transient_http_status_code

logger = get_logger(__name__)


def _is_retryable(exc: BaseException) -> bool:
    """Return True for transient Gemini API or transport errors."""
    if isinstance(exc, errors.APIError):
        return is_transient_http_status_code(getattr(exc, "code", None))

    if isinstance(exc, httpx.HTTPStatusError):
        return is_transient_http_status_code(exc.response.status_code)

    if isinstance(exc, (httpx.RequestError, asyncio.TimeoutError)):
        return True

    return False


_retry = retry(
    retry=retry_if_exception(_is_retryable),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=5, max=20),
    reraise=True,
)


class GeminiProvider:
    """
    Provider class for interacting with Google Gemini API.
    Handles model initialization and asynchronous content generation.
    """

    @property
    def MODEL_PROVIDER(self) -> str:
        """Return the LLM provider name."""
        return "Gemini"

    @property
    def MODEL_NAME(self) -> str:
        """Return the LLM model name."""
        return "gemini-3.1-flash-lite"

    @property
    def is_available(self) -> bool:
        """Return whether Gemini client initialization succeeded."""
        return self._client is not None

    def __init__(self, semaphore: asyncio.Semaphore) -> None:
        """
        Initialize the Gemini provider with API credentials and an injected semaphore.
        The semaphore should be created within an async context (e.g., lifespan)
        to ensure it is bound to the correct event loop.
        """
        self._semaphore = semaphore
        self._client = self._init_client()

    async def generate_content(
        self,
        contents: str,
        config: types.GenerateContentConfig,
    ) -> types.GenerateContentResponse:
        """Generate Gemini content and propagate provider errors."""
        response = await self._execute_generate_content(contents, config)
        self._log_generate_usage(response)
        return response

    def _init_client(self) -> genai.Client | None:
        """Return a Gemini client, or None when initialization is unavailable."""
        api_key = settings.gemini_api_key_free

        if not api_key:
            logger.warning("GeminiProvider initialize failed | reason: API key not set")
            return None

        try:
            return genai.Client(api_key=api_key)
        except Exception as e:
            logger.warning("GeminiProvider initialize failed | error: %s", str(e))
            return None

    def _get_client(self) -> genai.Client:
        """Return the initialized Gemini client, raising RuntimeError when unavailable."""
        if self._client is None:
            raise RuntimeError("Gemini client is not initialized.")
        return self._client

    @_retry
    async def _execute_generate_content(
        self, contents: str, config: types.GenerateContentConfig
    ) -> types.GenerateContentResponse:
        """Execute Gemini content generation with transient retries and concurrency control."""
        async with self._semaphore:
            return await self._get_client().aio.models.generate_content(
                model=self.MODEL_NAME,
                contents=contents,
                config=config,
            )

    def _log_generate_usage(self, response: types.GenerateContentResponse) -> None:
        """Log Gemini token usage metadata when present."""
        usage = getattr(response, "usage_metadata", None)
        logger.info(
            "GeminiProvider generate_content completed | prompt_tokens: %s, output_tokens: %s, total_tokens: %s",
            getattr(usage, "prompt_token_count", None),
            getattr(usage, "candidates_token_count", None),
            getattr(usage, "total_token_count", None),
        )
