"""
Groq API client for summarization and scene planning.

Uses llama-3.3-70b-versatile via the Groq cloud API for fast, structured
text summarization and scene planning tasks.
"""

import logging
import os
from typing import Optional

import requests

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

def _get_summary_model() -> str:
    return os.getenv("SUMMARY_MODEL", "llama-3.3-70b-versatile")

# Retry config
MAX_RETRIES = 3
TIMEOUT_SECONDS = 60

def groq_chat(
    prompt: str,
    system: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> str:
    """
    Send a chat completion request to the Groq API.

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
    if not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY not set. Add it to your .env file."
        )

    model = model or _get_summary_model()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(
                "Groq request | model=%s | attempt=%d | prompt_len=%d",
                model, attempt, len(prompt),
            )
            response = requests.post(
                GROQ_API_URL,
                headers=headers,
                json=payload,
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()

            data = response.json()
            text = data["choices"][0]["message"]["content"]
            logger.info(
                "Groq response | model=%s | response_len=%d",
                model, len(text),
            )
            return text

        except requests.exceptions.HTTPError as exc:
            last_error = exc
            status = exc.response.status_code if exc.response else "?"
            logger.warning(
                "Groq HTTP error %s on attempt %d: %s",
                status, attempt, exc,
            )
            # Rate limit — wait before retry
            if exc.response and exc.response.status_code == 429:
                import time
                time.sleep(2 * attempt)
                continue

        except Exception as exc:
            last_error = exc
            logger.warning("Groq error on attempt %d: %s", attempt, exc)

    raise RuntimeError(f"Groq API failed after {MAX_RETRIES} attempts: {last_error}")
