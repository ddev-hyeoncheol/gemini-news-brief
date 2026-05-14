from pydantic import BaseModel, Field, ConfigDict
from typing import Literal

AISectorType = Literal[
    "Macro",  # Macroeconomics (interest rates, inflation, GDP, employment)
    "Markets",  # Equities and bonds (stock trends, index analysis, IPOs)
    "Corporate",  # Corporate and industry (earnings, M&A, new products, executive news)
    "Crypto",  # Cryptocurrency (Bitcoin, blockchain, regulation)
    "RealEstate",  # Real estate (housing market, interest rate impact, construction)
    "Policy",  # Government fiscal policy (taxes, trade regulation, budget; excludes monetary policy)
    "Others",  # Other economic news that does not fit any category above
    "Invalid",  # Garbage or unprocessable content
]

AIFormatType = Literal[
    "Breaking",  # Brief factual news flash (e.g., "Nvidia up 3%")
    "Report",  # Standard news article (fact-based detailed coverage)
    "Analysis",  # In-depth analysis or research report (expert opinion or data interpretation)
    "Opinion",  # Expert column or op-ed driven by subjective viewpoints
    "PressRelease",  # Press release (promotional content from a company or institution)
    "Invalid",  # Garbage or unprocessable content
]


class LLMAnalysisResult(BaseModel):
    """Structured output schema for LLM-based news analysis results."""

    model_config = ConfigDict(
        json_schema_extra={"version": "0.1"},
    )

    news_id: str = Field(
        description="Exact unique identifier (News ID) from the provided <News> tag."
    )

    ai_sector: AISectorType = Field(
        description=(
            "Classify the economic sector of the news into exactly one of the provided categories. "
            "Use the following criteria: "
            "'Macro': Macroeconomic indicators, inflation, GDP, employment, or central bank monetary policy decisions (e.g., Fed rate decisions). "
            "'Markets': Stock and bond price movements, index analysis, fund flows, options, futures, or IPO news. "
            "'Corporate': Earnings reports, M&A, new products, executive appointments, or industry trends. "
            "'Crypto': Bitcoin, blockchain technology, or cryptocurrency regulation. "
            "'RealEstate': Housing market, mortgage rates, construction, or property investment. "
            "'Policy': Government fiscal policy, trade regulation, taxation, or budget announcements (exclude monetary policy, which belongs to Macro). "
            "'Others': Economic news that does not clearly fit any category above. "
            "'Invalid': Content is mostly empty, a paywall notice, a login prompt, or an error message."
        ),
    )
    ai_format: AIFormatType = Field(
        description=(
            "Classify the journalistic format of the article into exactly one of the provided types. "
            "Use the following criteria: "
            "'Breaking': Urgent or developing news flash with minimal context, typically under 3 short paragraphs. "
            "'Report': Standard news article with structured fact-based coverage. "
            "'Analysis': In-depth piece that interprets data or includes expert opinions. "
            "'Opinion': Column or op-ed driven by subjective viewpoints or personal insight. "
            "'PressRelease': Promotional content distributed directly by a company or institution. "
            "'Invalid': Content is mostly empty, a paywall notice, a login prompt, or an error message."
        ),
    )
    ai_sentiment: Literal["positive", "neutral", "negative"] = Field(
        description=(
            "Evaluate the inherent semantic tone of the news event as described in the text. "
            "This is a descriptive analysis of the event's nature, NOT a market price prediction. "
            "Use the following criteria: "
            "'positive': Beneficial developments or growth (e.g., strong earnings, technological breakthroughs, resolution of labor disputes). "
            "'negative': Adverse developments or risks (e.g., scandals, layoffs, regulatory fines, geopolitical instability). "
            "'neutral': Routine administrative updates, factual reporting of status quo, or events without a clear directional impact. "
            "If ai_sector is 'Invalid', default to 'neutral'."
        ),
    )
    ai_title: str = Field(
        max_length=200,
        description=(
            "Translate the news title into Korean. "
            "Preserve the original meaning exactly — do not summarize, paraphrase, or add context. "
            "If ai_sector is 'Invalid', return an empty string ('')."
        ),
    )
    ai_author: list[str] = Field(
        default_factory=list,
        description=(
            "Extract the individual author name(s) from the provided Raw Author metadata string. "
            "The string may contain irrelevant data separated by delimiters such as '|' (e.g., 'May 12 | John Doe | 100 views'). "
            "Include individual journalist or writer names only. "
            "Do NOT include publication names, news agencies (e.g., 'Reuters', 'AP'), or date strings. "
            "Return the result as a list of strings. If no individual author can be identified, return an empty list."
        ),
    )
    ai_summary: str = Field(
        max_length=500,  # Guard against oversized output before it reaches the database.
        description=(
            "Summarize the news content in 2 to 3 concise sentences. "
            "You MUST write the summary in Korean, regardless of the source language. "
            "The summary must be self-contained and capture the key facts, figures, and implications. "
            "The total character length MUST NOT exceed 500 characters. "
            "If ai_sector is 'Invalid', return an empty string ('')."
        ),
    )
    ai_content_clean: str = Field(
        description=(
            "Remove advertisements, promotional text, cookie notices, subscription prompts, "
            "navigation menus, and other boilerplate UI text from the provided Raw Content. "
            "Do NOT paraphrase, rewrite, or alter any original sentence in any way. "
            "Copy the remaining journalistic content exactly as written, preserving all original wording. "
            "If ai_sector is 'Invalid', return an empty string ('')."
        ),
    )


class LLMGenerateResult(BaseModel):
    """Wrapper for the full result of a single Gemini API batch call."""

    model_name: str = Field(description="LLM model name used for generation.")
    model_version: str = Field(description="LLM model version used for generation.")
    results: list[LLMAnalysisResult] = Field(
        default_factory=list,
        description="Parsed analysis results, one per input news item.",
    )
