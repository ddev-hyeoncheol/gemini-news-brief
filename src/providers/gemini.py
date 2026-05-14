from google import genai
from google.genai import types
from pydantic import TypeAdapter

from src.config.config import settings
from src.core.logger import get_logger
from src.models.entities.silver_news import SilverNewsModel
from src.models.schemas.llm import LLMAnalysisResult, LLMGenerateResult

logger = get_logger(__name__)

_RESULT_ADAPTER = TypeAdapter(list[LLMAnalysisResult])

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
    Handle model initialization and asynchronous batch content generation.
    """

    def __init__(self) -> None:
        """Initialize the Gemini provider with API credentials from settings."""
        self.api_key = settings.gemini_api_key_free
        self.model_name = DEFAULT_MODEL_NAME
        self.model_version = DEFAULT_MODEL_VERSION
        self.generate_default_config = DEFAULT_GENERATE_CONTENT_CONFIG
        self.client = None

        if not self.api_key:
            logger.error(
                "Gemini API key is missing | reason: GEMINI_API_KEY_FREE not set"
            )
            return

        try:
            self.client = genai.Client(api_key=self.api_key)
            logger.info("GeminiProvider initialized | model: %s", self.model_name)
        except Exception as e:
            logger.error("Gemini client initialization failed | error: %s", str(e))

    async def generate_content(
        self,
        items: list[SilverNewsModel],
        generate_content_config: types.GenerateContentConfig | None = None,
    ) -> LLMGenerateResult | None:
        """Generate LLM analysis results for a batch of Silver tier news items.
        Return an LLMGenerateResult containing parsed results and model metadata.
        Return None if the client is unavailable or an API error occurs.
        """
        if not self.client:
            logger.warning(
                "Gemini client not available | reason: initialization failed"
            )
            return None

        if not items:
            logger.info("Generate skipped | reason: no items")
            return LLMGenerateResult(
                model_name=self.model_name,
                model_version=self.model_version,
            )

        # Concatenate all news prompts into a single batch request.
        contents = "\n".join(self._get_news_prompt(item) for item in items)
        config = generate_content_config or self.generate_default_config

        try:
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config,
            )

            usage = response.usage_metadata
            logger.info(
                "Generate completed | prompt_tokens: %s, completion_tokens: %s, total_tokens: %s",
                usage.prompt_token_count,
                usage.candidates_token_count,
                usage.total_token_count,
            )

            # Explicitly validate response text with Pydantic for type safety and clear error reporting.
            parsed = _RESULT_ADAPTER.validate_json(response.text)

            return LLMGenerateResult(
                model_name=self.model_name,
                model_version=self.model_version,
                results=parsed,
            )
        except Exception as e:
            logger.error("Gemini content generation failed | error: %s", str(e))
            return None

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
