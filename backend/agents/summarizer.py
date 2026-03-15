"""
Summarizer agent — uses Groq API (llama-3.3-70b-versatile) to extract key concepts.

Output schema:
{
  "title": "...",
  "main_concepts": [
    {
      "name": "...",
      "explanation": "...",
      "visualization_opportunity": "..."
    }
  ]
}
"""

import logging
from typing import Any

from providers.groq_client import groq_chat
from utils.json_parser import extract_json

logger = logging.getLogger(__name__)

SUMMARIZER_PROMPT = """\
You are an expert at analyzing research papers and technical content.

Summarize the following content and extract its key concepts that could be visualized as animations.

Return ONLY a JSON object in this exact format — no explanation, no markdown, just the JSON:

{{
  "title": "<paper title>",
  "main_concepts": [
    {{
      "name": "<concept name>",
      "explanation": "<one-sentence explanation>",
      "visualization_opportunity": "<what would make a great visual scene>"
    }}
  ]
}}

Limit to the 5 most important concepts.
If there are no clear visualizable concepts in the content, return "main_concepts" as an empty array [].

LENGTH LIMITS (MANDATORY):
- Keep each `name` to at most 6 words.
- Keep each `explanation` to at most 16 words.
- Keep each `visualization_opportunity` to at most 18 words.
- Use concrete technical wording. Avoid long clauses.

Content:
{content}
"""


def run_summarizer(content: str) -> dict:
    """
    Summarize raw text content using Groq API and return structured concepts.

    Args:
        content: Raw text of the paper / document

    Returns:
        Parsed dict matching the schema above.
    """
    prompt = SUMMARIZER_PROMPT.format(content=content[:8000])  # Cap input length

    logger.info("Running summarizer on content (%d chars)", len(content))
    raw = groq_chat(prompt)
    logger.debug("Summarizer raw response: %s", raw[:500])

    try:
        result: dict = extract_json(raw)
    except ValueError:
        # Fallback: build a minimal result so the pipeline can continue
        logger.warning("Summarizer JSON parse failed; using fallback")
        result = {
            "title": "Unknown",
            "main_concepts": [
                {
                    "name": "Main Concept",
              "explanation": "Core idea from the provided content.",
              "visualization_opportunity": "Show a concise step-by-step mechanism diagram.",
                }
            ],
        }

    return result
