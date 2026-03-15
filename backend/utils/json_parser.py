"""
Lightweight JSON parser that extracts JSON objects / arrays from LLM responses.

LLMs often wrap JSON in markdown code fences or add explanatory prose around it.
This module strips all of that and returns pure Python objects.
"""

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Match a JSON block inside ```json ... ``` or ``` ... ```
_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)

# Match the outermost { ... } or [ ... ] in a string
_OBJ_RE = re.compile(r"(\{[\s\S]*\}|\[[\s\S]*\])")


def extract_json(text: str) -> Any:
    """
    Extract and parse the first JSON object or array from a string.

    Tries (in order):
      1. Parse the whole string as JSON.
      2. Extract a fenced code block and parse it.
      3. Find the outermost { } or [ ] and parse that.

    Raises:
        ValueError: if no valid JSON can be found in *text*.
    """
    # 1. Try the full string directly
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # 2. Try a fenced code block
    fence_match = _FENCE_RE.search(text)
    if fence_match:
        try:
            return json.loads(fence_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 3. Try the first outermost brace/bracket group
    obj_match = _OBJ_RE.search(text)
    if obj_match:
        try:
            return json.loads(obj_match.group(1))
        except json.JSONDecodeError:
            pass

    logger.warning("Could not extract valid JSON from LLM response:\n%s", text[:500])
    raise ValueError(f"No valid JSON found in response: {text[:200]!r}")
