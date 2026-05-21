import asyncio
import http

from google import genai
from google.genai import errors
from google.genai import types
from pydantic import TypeAdapter
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from src.config.config import settings
from src.core.logger import get_logger
from src.models.entities.silver_news import SilverNewsModel
from src.models.schemas.llm import LLMAnalysisResult, LLMGenerateResult

logger = get_logger(__name__)

_RESULT_ADAPTER = TypeAdapter(list[LLMAnalysisResult])

# Retry on transient server-side errors (503 overload, 429 rate limit).
# Exponential backoff waits between 5s and 20s, up to 3 attempts total.
_RETRYABLE_STATUS_CODES = (
    http.HTTPStatus.TOO_MANY_REQUESTS,  # 429
    http.HTTPStatus.SERVICE_UNAVAILABLE,  # 503
)


def _get_error_status_code(exc: BaseException) -> http.HTTPStatus | None:
    """Return the HTTP status code exposed by a Gemini API exception."""
    raw_status = getattr(exc, "code", None) or getattr(exc, "status", None)
    if raw_status is None:
        return None

    try:
        return http.HTTPStatus(int(raw_status))
    except (TypeError, ValueError):
        return None


def _is_retryable(exc: BaseException) -> bool:
    """Return True if the exception represents a transient server-side error worth retrying."""
    if not isinstance(exc, errors.APIError):
        return False

    return _get_error_status_code(exc) in _RETRYABLE_STATUS_CODES


_retry = retry(
    retry=retry_if_exception(_is_retryable),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=5, max=20),
    reraise=True,
)

# Configuration constants.
DEFAULT_MODEL_NAME = "gemini-3.1-flash-lite"
DEFAULT_MODEL_VERSION = "0.1"

# Prompt template for news augmentation.
SYSTEM_INSTRUCTION_PROMPT = """
You are an expert financial and economic news analyst.

[Core Task]
You will receive a batch of news items, each wrapped in <News> tags.
For EACH item, perform the following:
1. Classification: Identify the 'ai_sector' and 'ai_format' based on the specific criteria.
2. Sentiment Analysis: Evaluate the semantic tone (positive/neutral/negative) of the described events.
3. Content Extraction: Extract the authors and clean the body text exactly as written.
4. Translation & Summary: Translate the title and provide a concise summary in KOREAN.

[Language Rules]
- 'ai_summary' and 'ai_title' MUST be in Korean.
- For all other fields, follow the English labels and values specified in the schema.

[Constraint & Integrity]
- Return ONLY a valid JSON list. Do not include any conversational preamble or markdown backticks.
- CRITICAL: You must match each analysis result to its corresponding 'news_id' provided in the <News> tag. Never hallucinate or omit a news_id.
- You MUST return exactly one result object per input news item. Never skip or merge items, even if the content is unprocessable.
- If a news item is unprocessable (paywall, empty, or error message), strictly follow the 'Invalid' logic defined in the schema for all fields.

[Output Format]
Return the results strictly adhering to the LLMAnalysisResult schema.
"""

NEWS_PROMPT_TEMPLATE = """
<News>
News ID:    {news_id}
Category:   {category}
Source:     {source}
Title:      {title}
Raw Author: {author_raw}

Raw Content:
{content_raw}
</News>
"""

# Recommended configuration for structured output extraction from a batch of news items.
DEFAULT_GENERATE_CONTENT_CONFIG = types.GenerateContentConfig(
    system_instruction=SYSTEM_INSTRUCTION_PROMPT,
    temperature=0.05,
    top_p=0.95,
    max_output_tokens=65536,
    response_mime_type="application/json",
    response_schema=list[LLMAnalysisResult],
    safety_settings=[
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
    ],
)


class GeminiProvider:
    """
    Provider class for interacting with Google Gemini API.
    Handles model initialization and asynchronous batch content generation.
    """

    def __init__(self, semaphore: asyncio.Semaphore) -> None:
        """
        Initialize the Gemini provider with API credentials and an injected semaphore.
        The semaphore should be created within an async context (e.g., lifespan)
        to ensure it is bound to the correct event loop.
        """
        self.semaphore = semaphore
        self.api_key = settings.gemini_api_key_free
        self.model_name = DEFAULT_MODEL_NAME
        self.model_version = DEFAULT_MODEL_VERSION
        self.generate_default_config = DEFAULT_GENERATE_CONTENT_CONFIG
        self.client = None

        if not self.api_key:
            logger.warning(
                "Provider initialize failed | provider: gemini, reason: GEMINI_API_KEY_FREE not set"
            )
            return

        try:
            self.client = genai.Client(api_key=self.api_key)
            logger.info(
                "Provider initialize completed | provider: gemini, model: %s",
                self.model_name,
            )
        except Exception as e:
            logger.warning(
                "Provider initialize failed | provider: gemini, error: %s",
                str(e),
            )

    async def generate_content(
        self,
        items: list[SilverNewsModel],
        generate_content_config: types.GenerateContentConfig | None = None,
    ) -> LLMGenerateResult | None:
        """
        Generate structured LLM analysis for a batch of Silver tier news items.

        Return None when the client is unavailable or the request/response cannot be parsed.
        """
        if not self.client:
            logger.warning(
                "Provider generate skipped | provider: gemini, reason: initialization failed"
            )
            return None

        if not items:
            logger.info(
                "Provider generate skipped | provider: gemini, reason: no items"
            )
            return LLMGenerateResult(
                model_name=self.model_name,
                model_version=self.model_version,
            )

        # Concatenate all news prompts into a single batch request.
        contents = "\n".join(self._get_news_prompt(item) for item in items)
        config = generate_content_config or self.generate_default_config

        @_retry
        async def _call() -> types.GenerateContentResponse:
            # Acquire the semaphore inside the retry closure so the slot is released between retry attempts.
            async with self.semaphore:
                return await self.client.aio.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=config,
                )

        try:
            response = await _call()
        except Exception as e:
            logger.warning(
                "Provider generate failed | provider: gemini, reason: request failed, error: %s",
                str(e),
            )
            return None

        try:
            parsed = self._parse_generate_response(response)
        except Exception as e:
            logger.warning(
                "Provider generate failed | provider: gemini, reason: response parse failed, error: %s",
                str(e),
            )
            return None

        self._log_generate_usage(response)

        return LLMGenerateResult(
            model_name=self.model_name,
            model_version=self.model_version,
            results=parsed,
        )

    def _get_news_prompt(self, news: SilverNewsModel) -> str:
        """Return a formatted news prompt string for a single Silver tier news item."""
        return NEWS_PROMPT_TEMPLATE.format(
            news_id=news.news_id,
            category=news.category,
            source=news.source,
            title=news.title,
            author_raw=news.author_raw or "",
            content_raw=news.content_raw,
        )

    def _parse_generate_response(
        self, response: types.GenerateContentResponse
    ) -> list[LLMAnalysisResult]:
        """Parse Gemini JSON output into validated analysis results."""
        return _RESULT_ADAPTER.validate_json(response.text)

    def _log_generate_usage(self, response: types.GenerateContentResponse) -> None:
        """Log token usage metadata when Gemini includes it in the response."""
        usage = getattr(response, "usage_metadata", None)
        logger.info(
            "Provider generate completed | provider: gemini, prompt_tokens: %s, completion_tokens: %s, total_tokens: %s",
            getattr(usage, "prompt_token_count", None),
            getattr(usage, "candidates_token_count", None),
            getattr(usage, "total_token_count", None),
        )
