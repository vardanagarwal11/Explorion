"""
NVIDIA NIM API client for animation code generation.

Uses llama-3.3-70b-instruct via the NVIDIA NIM cloud API for high-quality
Manim and Remotion code generation.
"""

import logging
import os
from typing import Optional

import requests

logger = logging.getLogger(__name__)

NIM_API_KEY = os.getenv("NIM_API_KEY", "")
NIM_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
CODE_MODEL = os.getenv("CODE_MODEL", "meta/llama-3.3-70b-instruct")

# Retry config
MAX_RETRIES = 3
TIMEOUT_SECONDS = 120  # Code generation can be slower


def nim_generate(
    prompt: str,
    system: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.6,
    max_tokens: int = 8192,
) -> str:
    """
    Send a chat completion request to the NVIDIA NIM API.

    Args:
        prompt:      User message content.
        system:      Optional system message.
        model:       Model override (defaults to CODE_MODEL).
        temperature: Sampling temperature (lower = more deterministic code).
        max_tokens:  Maximum response tokens.

    Returns:
        The model's text response.

    Raises:
        RuntimeError: If the API call fails after retries.
    """
    if not NIM_API_KEY:
        raise RuntimeError(
            "NIM_API_KEY not set. Add it to your .env file."
        )

    model = model or CODE_MODEL
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    headers = {
        "Authorization": f"Bearer {NIM_API_KEY}",
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
                "NIM request | model=%s | attempt=%d | prompt_len=%d",
                model, attempt, len(prompt),
            )
            response = requests.post(
                NIM_API_URL,
                headers=headers,
                json=payload,
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()

            data = response.json()
            text = data["choices"][0]["message"]["content"]
            logger.info(
                "NIM response | model=%s | response_len=%d",
                model, len(text),
            )
            return text

        except requests.exceptions.HTTPError as exc:
            last_error = exc
            status = exc.response.status_code if exc.response else "?"
            logger.warning(
                "NIM HTTP error %s on attempt %d: %s",
                status, attempt, exc,
            )
            # Rate limit — wait before retry
            if exc.response and exc.response.status_code == 429:
                import time
                time.sleep(3 * attempt)
                continue

        except Exception as exc:
            last_error = exc
            logger.warning("NIM error on attempt %d: %s", attempt, exc)

    raise RuntimeError(f"NIM API failed after {MAX_RETRIES} attempts: {last_error}")
