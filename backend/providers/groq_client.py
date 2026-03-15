"""
API client for summarization and scene planning.

Uses openai/gpt-oss-120b via the NVIDIA cloud API for fast, structured
text summarization and scene planning tasks.
"""

import logging
import os
import sys
from typing import Optional

try:
    from openai import OpenAI
except ImportError:
    pass

logger = logging.getLogger(__name__)

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1"

def _get_summary_model() -> str:
    return os.getenv("SUMMARY_MODEL", "openai/gpt-oss-120b")

# Retry config
MAX_RETRIES = 3
TIMEOUT_SECONDS = 60

def groq_chat(
    prompt: str,
    system: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 1.0,
    max_tokens: int = 4096,
) -> str:
    """
    Send a chat completion request using the OpenAI SDK.

    Args:
        prompt:      User message content.
        system:      Optional system message.
        model:       Model override (defaults to SUMMARY_MODEL).
        temperature: Sampling temperature.
        max_tokens:  Maximum response tokens.

    Returns:
        The model's text response.

    Raises:
        RuntimeError: If the API call fails after retries.
    """
    if "openai" not in sys.modules:
        raise RuntimeError("Please install the 'openai' Python package.")

    if not NVIDIA_API_KEY:
        raise RuntimeError(
            "NVIDIA_API_KEY not set. Add it to your .env file."
        )

    model = model or _get_summary_model()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    client = OpenAI(
        base_url=NVIDIA_API_URL,
        api_key=NVIDIA_API_KEY
    )

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(
                "NVIDIA request | model=%s | attempt=%d | prompt_len=%d",
                model, attempt, len(prompt),
            )
            
            completion = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                top_p=1,
                max_tokens=max_tokens,
                stream=True
            )

            full_text = ""
            full_reasoning = ""

            for chunk in completion:
                if not getattr(chunk, "choices", None):
                    continue
                
                reasoning = getattr(chunk.choices[0].delta, "reasoning_content", None)
                if reasoning:
                    full_reasoning += reasoning
                    print(reasoning, end="")
                
                if chunk.choices and chunk.choices[0].delta.content is not None:
                    print(chunk.choices[0].delta.content, end="")
                    full_text += chunk.choices[0].delta.content

            logger.info(
                "\nNVIDIA response | model=%s | response_len=%d",
                model, len(full_text),
            )
            return full_text

        except Exception as exc:
            last_error = exc
            logger.warning("NVIDIA error on attempt %d: %s", attempt, exc)

    raise RuntimeError(f"NVIDIA API failed after {MAX_RETRIES} attempts: {last_error}")
